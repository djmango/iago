import json
import logging
import os
import threading
import time
from multiprocessing.pool import ThreadPool

import jsonschema
import numpy as np
from django.db.models import Q
from iago.settings import LOGGING_LEVEL_MODULE, MAX_DB_THREADS, SILKY_DEBUG_STR
from rest_framework import status, views
from rest_framework.response import Response
from silk.profiling.profiler import silk_profile

from v0 import ai, index, schemas
from v0.article import updateArticle
from v0.models import Content, Job, Skill, Topic
from v0.serializers import TopicSerializerAll
from v0.utils import search_fuzzy_cache

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)


class transform(views.APIView):
    """ transform texts """
    allowed_groups = {}

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.textsSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # embed
        embeds = ai.embedding_model.encode(request.data['texts'])

        return Response({'vectors': embeds}, status=status.HTTP_200_OK)


class matchSkills(views.APIView):
    """ take texts and return their embedding and related skills """

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.textsSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        texts = request.data['texts']

        # embed all texts in batch
        embeds = ai.embedding_model.encode(texts)

        results = []
        # find skills for each text/vector and populate results
        for embed in embeds:
            # find the closest skills
            skills, rankings, query_vector = index.skills_index.query(embed, k=10, min_distance=.21)  # NOTE these are hardcoded for now, important params if you want to change results
            skills_ranked = list(zip(*rankings))[0]  # rankings are keyed by pk which in skill objects case is the name

            # add to results
            results.append({
                'skills': skills_ranked,
                'embed': embed.tolist()
            })

        return Response({'results': results}, status=status.HTTP_200_OK)


class matchSkillsEmbeds(views.APIView):
    """ take embeds return their related skills """

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
            skills_ranked = list(zip(*rankings))[0]  # rankings are keyed by pk which in skill objects case is the name

            # add to results
            results.append({
                'skills': skills_ranked
            })

        return Response({'results': results}, status=status.HTTP_200_OK)


class adjacentSkills(views.APIView):
    """ take embeds return their related skills """
    @silk_profile(name=SILKY_DEBUG_STR+'Adjacent skills')
    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.adjacentSkillsSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        k = request.data['k'] if 'k' in request.data else 25
        temperature = float(request.data['temperature'])/100 if 'temperature' in request.data else .21
        query_skills = request.data['skills']

        # for each skill in the query, find its closest match in the skills database
        # skills is a list of results lists, but we only ask for 1 result per (sometimes if there are no matches it returns an empty list, so make sure that doesnt cause an error)
        skills = [search_fuzzy_cache(Skill, x)[0].first() for x in query_skills]

        adjacent_skills = []
        for skill, skill_name in zip(skills, query_skills):
            if skill is not None:
                # get adjacent skills for our skill
                results, rankings, query_vector = index.skills_index.query(skill.embedding_all_mpnet_base_v2, k=k+1, min_distance=temperature)  # we have to add one to k because the first result is always going to be the provided skill itself
                skills_ranked = list(zip(*rankings))[0]

                adjacent_skills.append({'name': skill.name, 'original': skill_name, 'adjacent': skills_ranked[1:k+1]})

        return Response({'skills': adjacent_skills}, status=status.HTTP_200_OK)


class updateContent(views.APIView):
    """ update scraped articles with their medium data """

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.kSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        k = int(request.data['k'])

        start = time.perf_counter()
        articles_uuid = list(Content.objects.filter(deleted=False).order_by('updated_on')[:k].values_list('uuid', flat=True))
        # articles_uuid = list(Content.objects.filter(thumbnail_alternative_url=None).values_list('uuid', flat=True))
        logger.info(f'Getting articles took {time.perf_counter()-start:.3f}s')
        logger.info(f'Updating data for {len(articles_uuid)} articles')

        pool = ThreadPool(processes=4)
        pool.map_async(updateArticle, articles_uuid)

        return Response({'status': 'started', 'count': len(articles_uuid)}, status=status.HTTP_200_OK)


class queryIndex(views.APIView):

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.queryKIndexSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = str(request.data['query'])
        k = int(request.data['k'])
        index_choice = str(request.data['index'])
        temperature = float(request.data['temperature'])/100 if 'temperature' in request.data else 0

        if index_choice == 'topic':
            query_index = index.topic_index
        elif index_choice == 'skill':
            query_index = index.skills_index
        elif index_choice == 'content':
            query_index = index.content_index
        elif index_choice == 'unsplash':
            query_index = index.unsplash_photo_index
        else:
            return Response({'status': 'error', 'response': f'invalid index {index_choice}'}, status=status.HTTP_400_BAD_REQUEST)

        results, rankings, query_vector = query_index.query(query, k, temperature)

        results_pk = results.values_list('pk', flat=True)
        results_ranked = []
        for pk, score in rankings[:k]:
            results_ranked.append(results.filter(pk=pk).values().first())

        return Response({'status': 'success', 'results': results_ranked, 'query_vector': query_vector, 'results_pk': results_pk}, status=status.HTTP_200_OK)


class modelAutocomplete(views.APIView):
    @silk_profile(name=SILKY_DEBUG_STR+'Model autocomplete')

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

        results, results_pk = search_fuzzy_cache(model, query, k, similarity_minimum)
        start = time.perf_counter()
        logger.debug(f'Evaluating results queryset k{len(results_pk)} took {time.perf_counter()-start:.3f}s')

        return Response({'status': 'success', 'results': results_pk}, status=status.HTTP_200_OK)


class adjacentSkillContent(views.APIView):
    """ search for content based on skills """
    @silk_profile(name=SILKY_DEBUG_STR+'Adjacent skill content')

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.adjacentSkillContentSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # required
        query_skills = request.data['skills']
        content_type = request.data['type']
        k: int = request.data['k']
        # optional
        length = request.data['length'] if 'length' in request.data else None
        page: int = request.data['page'] if 'page' in request.data else 0

        start = time.perf_counter()
        skills = [search_fuzzy_cache(Skill, x)[0].first() for x in query_skills]
        logger.debug(f'Singlethread skill map took {round(time.perf_counter() - start, 3)}s')

        # okay now we need to get adjacent skills
        adjacent_skills = []
        for skill, skill_name in zip(skills, query_skills):
            if skill is not None:
                # get adjacent skills for our skill
                results, rankings, query_vector = index.skills_index.query(skill.embedding_all_mpnet_base_v2, k=5)
                skills_ranked = list(zip(*rankings))[0]

                adjacent_skills.append({'name': skill.name, 'original': skill_name, 'adjacent': skills_ranked[1:]})
                skills.append(skill)

        # skills tag search
        content_to_return = Content.objects.filter(skills__in=skills)

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
        content_to_return = list(content_to_return.values('uuid', 'title', 'url', 'skills', 'thumbnail', 'thumbnail_alternative', 'popularity', 'provider', 'content_read_seconds', 'type', 'updated_on'))

        logger.debug(f'Content search took {round(time.perf_counter() - start, 3)}s')

        if len(content_to_return) == 0:
            return Response({'status': 'warning', 'response': 'No matching skills or content titles found', 'skills': [x.name for x in skills]}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({'content': content_to_return[page*k:(page+1)*k], 'skills': [x.name for x in skills], 'adjacent_skills': [x['name'] for x in adjacent_skills]}, status=status.HTTP_200_OK)


class searchContent(views.APIView):
    """ search for content based on skills """
    @silk_profile(name=SILKY_DEBUG_STR+'Search content')

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

        start = time.perf_counter()

        # if we have a query then we want to search content titles for it
        if query_string:
            results, rankings, query_vector = index.content_index.query(query_string, k=k*(page+2))  # plus 2 instead of 1 cuz im just gonna get extra results to ensure we have enough to ensure k values after filters
            content_to_return |= results

        # otherwise we have skills provided, for each skill in the query, find its closest match in the skills database
        elif query_skills:
            skills = [search_fuzzy_cache(Skill, x)[0] for x in query_skills]
            skills = [x[0] for x in skills if len(x) > 0]  # remove none values
            logger.debug(f'Singlethread skill map took {round(time.perf_counter() - start, 3)}s')

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


class recommendContent(views.APIView):
    """ generate recommendations for given a job title and content history """
    @silk_profile(name=SILKY_DEBUG_STR+'Recommend content')

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.recommendContentSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        start = time.perf_counter()
        # first match the free-form job title provided to one embedded in our database
        job: Job = search_fuzzy_cache(Job, request.data['position'])[0].first()

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
            if content_id_ranked in content_ids_to_return:  # ensure the result passed our filters
                content_ids_to_return_ranked.append(content_id_ranked)

        logger.info(f'Generating recommendations took {round(time.perf_counter() - start, 3)}s')
        return Response({'content_recommendations': content_ids_to_return_ranked[page*k:(page+1)*k], 'matched_job': job.name}, status=status.HTTP_200_OK)


class jobSkillMatch(views.APIView):
    """ take a job title string and return matching skills """

    def post(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.jobSkillMatchSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        start = time.perf_counter()
        job: Job = search_fuzzy_cache(Job, request.data['jobtitle'])[0].first()
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
            topic.create(name, ai.embedding_model.encode([name])[0])
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
    def get(self, request):
        return Response('alive', status=status.HTTP_200_OK)
