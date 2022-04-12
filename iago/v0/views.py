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
from django.db.models.functions import Now
from iago.permissions import HasGroupPermission
from rest_framework import status, views
from rest_framework.response import Response

from v0 import ai, index, schemas
from v0.models import Content, Job, Skill, Topic
from v0.serializers import TopicSerializerAll
from v0.utils import clean_str

logger = logging.getLogger(__name__)


class querySubmit(views.APIView):
    """ get related articles to the submitted query """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'POST': ['express_api']
    }

    def post(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.querySubmissionSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = request.data['query']
        k = request.data['k'] if 'k' in request.data else 5

        if 'text' not in request.data:  # query our database of content
            inference, vector = index.scrapedarticle_index.query(query, k=k)

            # format for humans
            neu_inferences = []
            for content, probability in inference:  # iterate through our inferences list and structure the data so that its easy for humans to analyze
                structured_topic = {
                    'name': str(content),  # title of the content
                    'url': str(content.url_response),  # url of the content
                    'probability': probability  # probablity of the inference being correct
                }
                neu_inferences.append(structured_topic)

        else:  # query the provided text
            # we will just split by sentences for now
            texts = [str(s) for s in re.split(r"(?<!^)\s*[.\n]+\s*(?!$)", request.data['text'])]

            # encode
            request_index = index.VectorIndex(texts)
            inference, vector = request_index.query(query, k=k)

            # format for humans
            neu_inferences = []
            for snippet, probability in inference:  # iterate through our inferences list and structure the data so that its easy for humans to analyze
                structured_topic = {
                    'snippet': snippet,  # snippet that was matched
                    'probability': probability  # probablity of the inference being correct
                }
                neu_inferences.append(structured_topic)

        return Response({'inference': neu_inferences}, status=status.HTTP_200_OK)


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
            skills: list[Skill] = index.skills_index.query_vector(embed, k=10, min_distance=.21)  # NOTE these are hardcoded for now, important params if you want to change results

            # add to results
            results.append({
                'skills': [x[0].name for x in skills],
                'embed': embed.tolist()
            })

        return Response({'results': results}, status=status.HTTP_200_OK)


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
            skills: list[Skill] = index.skills_index.query_vector(embed, k=10, min_distance=.21)  # NOTE these are hardcoded for now, important params if you want to change results

            # add to results
            results.append({
                'skills': [x[0].name for x in skills]
            })

        return Response({'results': results}, status=status.HTTP_200_OK)


class adjacentSkills(views.APIView):
    """ take embeds return their related skills """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['scrapy_spider']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.adjacentSkillsSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        k = request.data['k'] if 'k' in request.data else 25
        temperature = int(request.data['temperature'])/100 if 'temperature' in request.data else .21

        skills = []
        # for each skill in the query, find its closest match in the skills database
        for skill_name in request.data['skills']:
            skill = Skill.objects.annotate(similarity=TrigramSimilarity('name', skill_name)).filter(similarity__gt=0.7).order_by('-similarity').first()
            if skill is not None:
                # get adjacent skills for our skill
                r = index.skills_index.query_vector(skill.embedding_all_mpnet_base_v2, k=k, min_distance=temperature)

                skills.append({'name': skill.name, 'original': skill_name, 'adjacent': [x[0].name for x in r]})

        return Response({'skills': skills}, status=status.HTTP_200_OK)


def transformArticles(articles):
    """ transform articles into vectors and save to db """
    # get their contents and embed them
    logger.info(f'generating vectors for {len(articles)}')
    contents = [x.content for x in articles]
    vectors = ai.embedding_model.model.encode(contents, show_progress_bar=True)

    # update the queryset articles with the new embeddings
    logger.info('saving vectors..')
    for article, vector in zip(articles, vectors):
        article.embedding_all_mpnet_base_v2 = vector.tolist()
        article.save()


class transformContents(views.APIView):
    """ transform all scraped articles and saves the embeddings """
    permission_classes = [HasGroupPermission]
    allowed_groups = {}

    def get(self, request):
        # get all articles with no embeddings
        start = time.perf_counter()
        articles: list[Content] = list(Content.objects.filter(embedding_all_mpnet_base_v2__isnull=True))

        # start transforming in a thread
        threading.Thread(target=transformArticles, name=f'transformArticles_{len(articles)}', args=[articles]).start()
        return Response({'status': 'started', 'count': len(articles), 'time': round(time.perf_counter()-start, 3)}, status=status.HTTP_200_OK)


def updateArticle(article_uuid):
    """ seperate function for job pooling """
    start = time.perf_counter()

    article: Content = Content.objects.get(uuid=article_uuid)

    postID = article.url.split('/')[-1].split('-')[-1]
    try:
        r = requests.get(f'https://medium.com/_/api/posts/{postID}')
        data = json.loads(r.text[16:])

        # if user deleted the article or their account then we mark it as deleted
        if data['success'] == False:
            logger.error(f'Failed to get article {article.url}, {data["error"]}')
            if 'deleted' in data['error']: # though its possible we just got rate limited, so make sure to check the error
                article.deleted = True
                article.updated_on = Now()
                article.save()
            return

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
                if '.gif' in article.thumbnail: # we dont want gifs as preview, so if we happen to find an image to replace it in the body then we can use that instead
                    article.thumbnail = f"https://miro.medium.com/{par['metadata']['id']}"
            else:
                paragraphs.append(clean_str(par['text']))

        article.content = '\n\n'.join(paragraphs)

        for t in post['virtuals']['tags']:
            if t['type'] == 'Tag':
                if t['slug'] not in article.tags:
                    article.tags.append(t['slug'])

        # we really hate gifs
        if '.gif' in article.thumbnail:
            article.thumbnail = None
        article.save()
        logger.info(f'Updated {article.title} in {time.perf_counter()-start:.3f}s')
    except Exception as e:
        logger.error(e)  # we do get banned if we have hit too fast - about 10 requests per second i think but not sure


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

        p = ThreadPool(processes=5)
        p.map_async(updateArticle, articles_uuid)

        return Response({'status': 'started', 'count': len(articles_uuid)}, status=status.HTTP_200_OK)


class searchSkills(views.APIView):
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['express_api']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.queryKSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = str(request.data['query'])
        k = int(request.data['k'])

        skills = Skill.objects.annotate(similarity=TrigramSimilarity('name', query)).filter(similarity__gt=0.3).order_by('-similarity')
        return Response({'skills': [str(x.name) for x in skills][:k]}, status=status.HTTP_200_OK)


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

        strict = request.data['strict'] if 'strict' in request.data else False
        type = request.data['type'] if 'type' in request.data else None
        length = request.data['length'] if 'length' in request.data else None

        start = time.perf_counter()
        skills = []
        # for each skill in the query, find its closest match in the skills database
        for skill_name in request.data['skills']:
            skill = Skill.objects.annotate(similarity=TrigramSimilarity('name', skill_name)).filter(similarity__gt=0.7).order_by('-similarity').first()
            if skill is not None:
                skills.append(skill)
        logger.info(f'Skill search took {round(time.perf_counter() - start, 3)}s')

        if len(skills) == 0:
            return Response({'status': 'error', 'response': 'No matching skills found'}, status=status.HTTP_200_OK)

        # apply filters
        start = time.perf_counter()
        # skills filter
        if strict:
            content = Content.objects.filter(skills=skills)
        else:
            content = Content.objects.filter(skills__in=skills)

        # type filter
        if type:
            content = content.filter(type__in=type)

        # length filter
        if length:
            content = content.filter(content_read_seconds__lte=length[1], content_read_seconds__gte=length[0])

        # perform the transaction
        content = list(content.values('uuid', 'title', 'url', 'skills', 'thumbnail', 'popularity', 'provider', 'content_read_seconds', 'type', 'updated_on'))
        
        logger.info(f'Content search took {round(time.perf_counter() - start, 3)}s')

        k = request.data['k'] if 'k' in request.data else len(content)
        return Response({'content': content[:k], 'skills': [x.name for x in skills]}, status=status.HTTP_200_OK)


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
        jobs = Job.objects.annotate(similarity=TrigramSimilarity('name', request.data['jobtitle'])).filter(similarity__gt=0.3).order_by('-similarity')
        job: Job = jobs.first()
        logger.info(f'Trigram took {round(time.perf_counter() - start, 3)}s')

        if job is None:  # if we have no matched jobs just return an empty list since we only want to search using existing jobtitles with embeds, not generate new ones
            return Response({'skills': []}, status=status.HTTP_200_OK)
        k = request.data['k'] if 'k' in request.data else 7

        # search index
        start = time.perf_counter()
        results = index.skills_index.query_vector(np.array(job.embedding_all_mpnet_base_v2), k)
        skills = [str(result[0].name) for result in results]
        logger.info(f'Index search took {round(time.perf_counter() - start, 3)}s')

        return Response({'jobtitle': str(job.name), 'skills': skills}, status=status.HTTP_200_OK)

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
