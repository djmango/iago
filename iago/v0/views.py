import json
import logging
import re
import threading
import time
from multiprocessing.pool import ThreadPool

import jsonschema
import numpy as np
import requests
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from django.db.models.functions import Now
from iago.permissions import HasGroupPermission
from iago.settings import DEBUG, LOGGING_LEVEL_MODULE, MAX_DB_THREADS
from rest_framework import status, views
from rest_framework.response import Response
from silk.profiling.profiler import silk_profile

from v0 import ai, index, schemas
from v0.models import Content, Job, Skill, Topic
from v0.serializers import TopicSerializerAll
from v0.utils import clean_str, search_fuzzy_cache

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)


class transform(views.APIView):
    """ transform texts """
    permission_classes = [HasGroupPermission]
    allowed_groups = {}

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.textsSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # embed
        vectors = ai.embedding_model.model.encode(request.data['texts'])

        return Response({'vectors': vectors}, status=status.HTTP_200_OK)


class matchSkills(views.APIView):
    """ take texts and return their embedding and related skills """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['scrapy_spider']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.textsSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        texts = request.data['texts']

        # embed all texts in batch
        embeds = ai.embedding_model.model.encode(texts)

        results = []
        # find skills for each text/vector and populate results
        for embed in embeds:
            # find the closest skills
            skills, rankings, query_vector = index.skills_index.query(embed, k=10, min_distance=.21)  # NOTE these are hardcoded for now, important params if you want to change results
            skills_ranked = list(zip(*rankings))[0] # rankings are keyed by pk which in skill objects case is the name

            # add to results
            results.append({
                'skills': skills_ranked,
                'embed': embed.tolist()
            })

        return Response({'results': results}, status=status.HTTP_200_OK)

# TODO: merge these two functions

class matchSkillsEmbeds(views.APIView):
    """ take embeds return their related skills """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['scrapy_spider']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.embedsSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        # find skills for each text/vector and populate results
        for embed in request.data['embeds']:
            # find the closest skills
            skills, rankings, query_vector = index.skills_index.query(embed, k=10, min_distance=.21)  # NOTE these are hardcoded for now, important params if you want to change results
            skills_ranked = list(zip(*rankings))[0] # rankings are keyed by pk which in skill objects case is the name

            # add to results
            results.append({
                'skills': skills_ranked
            })

        return Response({'results': results}, status=status.HTTP_200_OK)


class adjacentSkills(views.APIView):
    """ take embeds return their related skills """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['scrapy_spider']
    }

    @silk_profile(name='Adjacent Skills')
    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.adjacentSkillsSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        k = request.data['k'] if 'k' in request.data else 25
        temperature = float(request.data['temperature'])/100 if 'temperature' in request.data else .21

        # for each skill in the query, find its closest match in the skills database
        pool = ThreadPool(processes=MAX_DB_THREADS)
        skills = pool.starmap(search_fuzzy_cache, [(Skill, skill) for skill in request.data['skills']])
        skills = [x[0] for x in skills] # skills is a list of results lists, but we only ask for 1 result per
        pool.close()

        skills_result = []
        for skill, skill_name in zip(skills, request.data['skills']):
            if skill is not None:
                # get adjacent skills for our skill
                results, rankings, query_vector = index.skills_index.query(skill.embedding_all_mpnet_base_v2, k=k+1, min_distance=temperature)  # we have to add one to k because the first result is always going to be the provided skill itself
                skills_ranked = list(zip(*rankings))[0]

                skills_result.append({'name': skill.name, 'original': skill_name, 'adjacent': skills_ranked[1:]})

        return Response({'skills': skills_result}, status=status.HTTP_200_OK)

def updateArticle(article_uuid):
    """ seperate function for job pooling """
    start = time.perf_counter()

    article: Content = Content.objects.get(uuid=article_uuid)

    postID = article.url.split('/')[-1].split('-')[-1]
    try:
        r = requests.get(f'https://medium.com/_/api/posts/{postID}')
        if not r.status_code == 200:
            raise Exception(f'Failed to get article {article.title}, status code {r.status_code}')
            # cause slowdown on 429
        data = json.loads(r.text[16:])

        # if user deleted the article or their account then we mark it as deleted
        if data['success'] == False:
            logger.error(f'Failed to get article {article.url}, {data["error"]}')
            if 'deleted' in data['error']:  # though its possible we just got rate limited, so make sure to check the error
                article.deleted = True
                article.updated_on = Now()
                article.save()
            return
        else:
            article.deleted = False

        post = data['payload']['value']

        article.url = post['mediumUrl']
        article.title = post['title']

        # author is annoying
        if 'references' in data['payload'] and 'User' in data['payload']['references']:
            article.author = data['payload']['references']['User'].popitem()[1]['name']
        elif '@' in article.url:
            article.author = article.url.split('@')[1].split('/')[0]

        article.subtitle = post['virtuals']['subtitle']
        article.thumbnail = f"https://miro.medium.com/{post['virtuals']['previewImage']['imageId']}"  # https://miro.medium.com/0*5avpGviF6Pf1EyUL.jpg
        article.content_read_seconds = int(float(post['virtuals']['readingTime'])*60)
        article.popularity['medium'] = {'totalClapCount': post['virtuals']['totalClapCount']}
        article.provider = 'medium'

        # NOTE: this is an example of a medium article but its actually a video https://medium.com/@digitalprspctv/vsco-style-images-in-3-simple-steps-photoshop-4de7e74b29c8

        # concat paragraphs
        paragraphs = []
        for par in post['content']['bodyModel']['paragraphs']:
            if par['type'] == 4:
                if '.gif' in article.thumbnail:  # we dont want gifs as preview, so if we happen to find an image to replace it in the body then we can use that instead
                    article.thumbnail = f"https://miro.medium.com/{par['metadata']['id']}"
            else:
                paragraphs.append(clean_str(par['text']))

        article.content = '\n\n'.join(paragraphs)

        for t in post['virtuals']['tags']:
            if t['type'] == 'Tag':
                if t['slug'] not in article.tags:
                    article.tags.append(t['slug'])

        # we really hate gifs - also null out the default image, no point of keeping it
        if '.gif' in article.thumbnail or article.thumbnail == 'https://miro.medium.com/':
            article.thumbnail = None

        # get us an alternate thumbnail from our images library
        # if article.thumbnail_alternative is None or article.thumbnail_alternative_url is None or not article.thumbnail_alternative.url_alive:
        #     img = index.image_index.query(article.embedding_all_mpnet_base_v2, k=1)[0][0]
        #     article.thumbnail_alternative = img
        #     article.thumbnail_alternative_url = img.url
        
        article.save()
        logger.info(f'Updated {article.title} in {time.perf_counter()-start:.3f}s')
    except Exception as e:
        logger.error(str(e))  # we do get banned if we have hit too fast - about 10 requests per second i think but not sure
        if 'Post was removed by the user' or 'Account is suspended' in str(e):
            article.deleted = True
            logger.error(f'Logging {article.title} as deleted')
            article.save()


class updateContent(views.APIView):
    """ update scraped articles with their medium data """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['express_api']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.kSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        k = int(request.data['k'])

        start = time.perf_counter()
        articles_uuid = list(Content.objects.all().order_by('updated_on')[:k].values_list('uuid', flat=True))
        logger.info(f'Getting articles took {time.perf_counter()-start:.3f}s')
        logger.info(f'Updating data for {len(articles_uuid)} articles')

        pool = ThreadPool(processes=5)
        pool.map_async(updateArticle, articles_uuid)

        return Response({'status': 'started', 'count': len(articles_uuid)}, status=status.HTTP_200_OK)

# TODO: create cache for embeddings or maybe a database call since they are deterministic
class queryIndex(views.APIView):
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['express_api']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.queryKIndexSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = str(request.data['query'])
        k = int(request.data['k'])
        index_choice = str(request.data['index'])

        if index_choice == 'topic':
            query_index = index.topic_index
        elif index_choice == 'skill':
            query_index = index.skills_index
        elif index_choice == 'content':
            query_index = index.content_index
        else:
            return Response({'status': 'error', 'response': f'invalid index {index_choice}'}, status=status.HTTP_400_BAD_REQUEST)

        results, rankings, query_vector = query_index.query(query, k)

        results_pk = results.values_list('pk', flat=True)
        results_ranked = []
        for pk, score in rankings:
            results_ranked.append(results.filter(pk=pk).values().first())

        return Response({'status': 'success', 'results': results_ranked, 'query_vector': query_vector, 'results_pk': results_pk}, status=status.HTTP_200_OK)

class modelAutocomplete(views.APIView):
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['express_api']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.autocompleteSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = str(request.data['query'])
        model_choice = str(request.data['model'])
        k = int(request.data['k'])
        similarity_minimum = float(request.data['similarity_minimum']/100) if 'similarity_minimum' in request.data else 0.3

        if model_choice == 'topic':
            model = Topic
        elif model_choice == 'skill':
            model = Skill
        elif model_choice == 'content':
            model = Content
        else:
            return Response({'status': 'error', 'response': f'invalid model {model_choice}'}, status=status.HTTP_400_BAD_REQUEST)

        results = search_fuzzy_cache(model, query, k, similarity_minimum)
        results_pk = results.values_list('pk', flat=True)

        return Response({'status': 'success', 'results': results_pk}, status=status.HTTP_200_OK)

class searchContent(views.APIView):
    """ search for content based on skills """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['express_api']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.searchContentSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # required
        content_type = request.data['type']
        k: int = request.data['k']
        # oneOf
        query_string = request.data['searchtext'] if 'searchtext' in request.data else None
        query_skills = request.data['skills'] if 'skills' in request.data else None
        # optional
        strict = request.data['strict'] if 'strict' in request.data else False
        length = request.data['length'] if 'length' in request.data else None
        page: int = request.data['page'] if 'page' in request.data else 0

        content_to_return = Content.objects.none()
        skills = []

        start = time.perf_counter()

        # if we have a query then we want to search content titles for it
        if query_string:
            results, rankings, query_vector = index.content_index.query(query_string, k=k*(page+2)) # plus 2 instead of 1 cuz im just gonna get extra results to ensure we have enough to ensure k values after filters
            content_to_return |= results

        # otherwise we have skills provided, for each skill in the query, find its closest match in the skills database
        elif query_skills:
            pool = ThreadPool(processes=MAX_DB_THREADS)
            skills.extend([x[0] for x in pool.starmap(search_fuzzy_cache, [(Skill, skill) for skill in query_skills])])
            pool.close()
            logger.debug(f'Multithread skill map took {round(time.perf_counter() - start, 3)}s')
            skills = [x for x in skills if x is not None]  # remove none values

            # skills tag search
            if strict and len(skills) > 0:
                content_to_return |= Content.objects.filter(skills=skills)
            elif len(skills) > 0:
                content_to_return |= Content.objects.filter(skills__in=skills)

        # apply filters to content_to_return queryset
        # type filter
        content_to_return = content_to_return.filter(type__in=content_type)

        # length filter
        if length:
            content_to_return = content_to_return.filter(content_read_seconds__lte=length[1], content_read_seconds__gte=length[0])

        # popularity filter - remove anything that has no likes, a quick cheat for basic quality assurance NOTE this only works for medium articles
        content_to_return = content_to_return.filter(~Q(provider='medium') | (Q(provider='medium') & Q(popularity__medium__totalClapCount__gt=0)))

        # unique filter
        content_to_return = content_to_return.distinct('uuid')

        # perform the transaction
        content_to_return = list(content_to_return.values('uuid', 'title', 'url', 'skills', 'thumbnail', 'popularity', 'provider', 'content_read_seconds', 'type', 'updated_on'))

        # build a ranked list of the content from the rankings provided by the indexer, which are already ordered by similarity
        content_to_return_ids = [x['uuid'] for x in content_to_return]
        if query_string:
            content_to_return_ranked = []
            for content_id, score in rankings:
                if content_id in content_to_return_ids:
                    content_to_return_ranked.append(content_to_return[content_to_return_ids.index(content_id)])
        else:
            content_to_return_ranked = content_to_return

        logger.debug(f'Content search took {round(time.perf_counter() - start, 3)}s')

        if len(content_to_return) == 0:
            return Response({'status': 'warning', 'response': 'No matching skills or content titles found', 'skills': [x.name for x in skills]}, status=status.HTTP_200_OK)
        else:
            return Response({'content': content_to_return_ranked[page*k:(page+1)*k], 'skills': [x.name for x in skills]}, status=status.HTTP_200_OK)


class recomendContent(views.APIView):
    """ generate recommendations for given a job title and content history """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['express_api']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.recomendContentSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        start = time.perf_counter()
        # first match the free-form job title provided to one embedded in our database
        job: Job = search_fuzzy_cache(Job, request.data['position'])[0]

        # next get content objects with the provided content history ids
        content_history: list[Content] = []
        for content_id in request.data['lastconsumedcontent']:
            try:
                content = Content.objects.get(uuid=content_id, deleted=False)
                content_history.append(content)
            except Content.DoesNotExist:
                return Response({'status': 'error', 'response': f'Content with id {content_id} does not exist or has been deleted'}, status=status.HTTP_400_BAD_REQUEST)

        # now get the center of the content history embeddings
        content_history_vectors = np.array([x.embedding_all_mpnet_base_v2 for x in content_history]).astype(np.float32)
        content_history_center = np.average(content_history_vectors, axis=0)

        # get the weights of job and history and compute the center of the recomendation in the embedding space
        job_weight, history_weight = request.data['weights'] if 'weights' in request.data else [1, 1]
        recomendation_center = np.average([np.array(job.embedding_all_mpnet_base_v2), content_history_center], axis=0, weights=[job_weight, history_weight])

        # now get the closest k content to the recomendation center via our faiss index
        k: int = request.data['k']
        page: int = request.data['page'] if 'page' in request.data else 0
        temperature = float(request.data['temperature']/100) if 'temperature' in request.data else 0
        results, rankings, query_vector = index.content_index.query(recomendation_center, k=k*(page+2), min_distance=temperature)
        content_to_return = results
        
        # apply filters
        content_type = request.data['type'] if 'type' in request.data else None
        length = request.data['length'] if 'length' in request.data else None
        # type filter
        if content_type:
            content_to_return = content_to_return.filter(type__in=content_type)

        # length filter
        if length:
            content_to_return = content_to_return.filter(content_read_seconds__lte=length[1], content_read_seconds__gte=length[0])

        # popularity filter - remove anything that has no likes, a quick cheat for basic quality assurance NOTE this only works for medium articles
        content_to_return = content_to_return.filter(~Q(provider='medium') | (Q(provider='medium') & Q(popularity__medium__totalClapCount__gt=0)))

        # unique filter
        content_to_return = content_to_return.distinct('uuid')

        # evaluate the queryset and get the ids
        content_ids_to_return = list(content_to_return.values_list('uuid', flat=True))

        # build a ranked list of the content ids from the rankings provided by the indexer, which are already ordered by similarity to the recomendation center vector
        content_ids_to_return_ranked = []
        for content_id_ranked, score in rankings:
            if content_id_ranked in content_ids_to_return: # ensure the result passed our filters
                content_ids_to_return_ranked.append(content_id_ranked)

        logger.info(f'Generating recommendations took {round(time.perf_counter() - start, 3)}s')
        return Response({'content_recommendations': content_ids_to_return_ranked[page*k:(page+1)*k], 'matched_job': job.name}, status=status.HTTP_200_OK)


class jobSkillMatch(views.APIView):
    """ take a job title string and return matching skills """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'POST': ['express_api']
    }

    def post(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.jobSkillMatchSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        start = time.perf_counter()
        job: Job = search_fuzzy_cache(Job, request.data['jobtitle'])[0]
        logger.info(f'Trigram took {round(time.perf_counter() - start, 3)}s')

        if job is None:  # if we have no matched jobs just return an empty list since we only want to search using existing jobtitles with embeds, not generate new ones
            return Response({'skills': []}, status=status.HTTP_200_OK)
        k = request.data['k'] if 'k' in request.data else 7

        # search index
        start = time.perf_counter()
        
        results, rankings, query_vector = index.skills_index.query(job.embedding_all_mpnet_base_v2, k=k)
        skills_ranked = list(zip(*rankings))[0]
        logger.info(f'Index search took {round(time.perf_counter() - start, 3)}s')

        return Response({'jobtitle': str(job.name), 'skills': skills_ranked}, status=status.HTTP_200_OK)

# Topic CRUD class views


class topicList(views.APIView):
    def get(self, request):
        return Response([str(topic) for topic in Topic.objects.all()], status=status.HTTP_200_OK)


class topic(views.APIView):
    """ CRUD for specified topic """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['express_api']
    }

    def get(self, request, name: str):
        name = name.lower()
        if Topic.objects.filter(name=name).count() > 0:
            return Response(TopicSerializerAll(Topic.objects.get(name=name)).data, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'error', 'response': f'topic {name} not found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, name: str):
        name = name.lower()
        if Topic.objects.filter(name=name).count() > 0:
            return Response({'status': 'exists', 'response': f'topic {name} already exists'}, status=status.HTTP_302_FOUND)
        else:
            topic = Topic()
            topic.create(name)
            topic.save()
            threading.Thread(target=index.topic_index.generate_index).start()
            return Response({'status': 'success', 'response': f'{name} created'}, status=status.HTTP_201_CREATED)

    def delete(self, request, name: str):
        name = name.lower()
        if Topic.objects.filter(name=name).count() > 0:
            Topic.objects.get(name=name).delete()
            threading.Thread(target=index.topic_index.generate_index).start()
            return Response({'status': 'success', 'response': f'{name} deleted'}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'error', 'response': f'topic {name} not found'}, status=status.HTTP_404_NOT_FOUND)


class alive(views.APIView):
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['__all__']
    }

    def get(self, request):
        return Response('alive', status=status.HTTP_200_OK)
