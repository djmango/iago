import logging
import threading
import time
from multiprocessing.pool import ThreadPool

import jsonschema
import numpy as np
from django.core.cache import cache
from django.db import models
from drf_spectacular.utils import extend_schema
from iago.settings import DEBUG, LOGGING_LEVEL_MODULE
from rest_framework import status, views
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.request import Request

from v0 import ai, index
from v0 import serializers
from v0.article import updateArticle
from v0.models import Content, Job, MindtoolsSkillGroup, Skill, Topic, HUMAN_TO_MODEL
from v0.pdf import ingestContentPDF
from v0.schemas import schemas_request, schemas_response
from v0.serializers import fileUploadSerializer
from v0.utils import allowedFile, is_valid_uuid, search_fuzzy_cache

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)

# * Skills Views


class skills_match(views.APIView):
    """ take texts and return their embedding and related skills """

    def get(self, request: Request):
        return self.post(request)

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.texts)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

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


class skills_match_embeds(views.APIView):
    """ take embeds return their related skills """

    def get(self, request: Request):
        return self.post(request)

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.embeds)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

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


class skills_adjacent(views.APIView):
    """ take embeds return their related skills """

    def get(self, request: Request):
        return self.post(request)

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.skills_adjacent)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

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


# * Index Views


class index_rebuild(views.APIView):
    """ rebuild the index """

    def put(self, request: Request, index_choice: str):
        if index_choice == 'topic':
            query_index = index.topic_index
        elif index_choice == 'skill':
            query_index = index.skills_index
        elif index_choice == 'content':
            query_index = index.content_index
        elif index_choice == 'unsplash':
            query_index = index.unsplash_photo_index
        elif index_choice == 'vodafone':
            query_index = index.vodafone_index
        else:
            return Response({'response': f'invalid index {index_choice}'}, status=status.HTTP_400_BAD_REQUEST)

        query_index._generate_index()  # it aint smooth, worried about mem-lock but whatever

        return Response({'response': 'success'}, status=status.HTTP_200_OK)


class index_query(views.APIView):

    def post(self, request: Request, index_choice: str):
        try:
            jsonschema.validate(request.data, schema=schemas_request.query_k_temperature_fields)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = str(request.data['query'])
        k = int(request.data['k'])
        temperature = float(request.data.get('temperature', 0)/100)  # default to 0
        page: int = request.data.get('page', 0)

        if index_choice == 'topic':
            query_index = index.topic_index
        elif index_choice == 'skill':
            query_index = index.skills_index
        elif index_choice == 'content':
            query_index = index.content_index
        elif index_choice == 'unsplash':
            query_index = index.unsplash_photo_index
        elif index_choice == 'vodafone':
            query_index = index.vodafone_index
        else:
            return Response({'response': f'invalid index {index_choice}'}, status=status.HTTP_400_BAD_REQUEST)

        # get model and fields
        model = query_index.model
        model_fields = ['pk'] + [x.name for x in model._meta.get_fields()]

        # validate requested return fields
        fields = request.data.get('fields', ['pk'])  # default to just pk returned
        if any(x not in model_fields for x in fields):
            return Response(f'{model} does not have the following fields: {[x for x in fields if x not in model_fields]}', status=status.HTTP_400_BAD_REQUEST)

        if not 'pk' in fields: # must return pk to do the ranking later
            fields.append('pk')

        # do the actual search
        results, rankings, query_vector = query_index.query(query, k*(page+1), temperature)
        
        results_pk_to_return_ranked, scores = zip(*[(x, score) for x, score in rankings[page*k:(page+1)*k]])

        # finally get the fields from the results that we want
        if fields == ['pk']: # no need to hit the db again if we just want the pks, also makes it so we dont need to rerank
            results_to_return = results_pk_to_return_ranked
        else: # otherwise return a list of dicts if we want multiple fields. means we also need to rank the results of the queryset since the database hit is unordered
            results_to_return = list(results.values(*fields))

            # Sort based on ranking.
            # One thing to note is that the results list is not ordered or offset/truncated, but the results_pk list is, 
            # so a workaround to sorting the entire list which potentially could be really long based on the k and page value is to asssign -1
            # to the pk of any results that are not in the results_pk_to_return_ranked list, which potentially are actually higher ranked but
            # we don't want to return them because of the k/page value
            results_to_return = sorted(results_to_return, key=lambda result: results_pk_to_return_ranked.index(result['pk']) if result['pk'] in results_pk_to_return_ranked else -1)

            # Now that we have the results sorted, we can return the correct number and offset of results based on the page/k value
            results_to_return = results_to_return[page*k:(page+1)*k]

            # Annotate with score that we used to rank
            for i, result in enumerate(results_to_return):
                result['score'] = scores[i]

        return Response({'results': results_to_return, 'query_vector': query_vector}, status=status.HTTP_200_OK)

# * Content Views


class content_update(views.APIView):
    """ update scraped articles with their medium data """

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.k)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        k = int(request.data['k'])

        start = time.perf_counter()
        articles_uuid = list(Content.objects.filter(deleted=False).order_by('updated_on')[:k].values_list('uuid', flat=True))
        logger.info(f'Getting articles took {time.perf_counter()-start:.3f}s')
        logger.info(f'Updating data for {len(articles_uuid)} articles')

        pool = ThreadPool(processes=4)
        pool.map_async(updateArticle, articles_uuid)

        return Response({'response': 'started', 'count': len(articles_uuid)}, status=status.HTTP_200_OK)


class content_file_upload(views.APIView):  # vodafone
    """ file upload and full processing, however only pdf format, supports multiple file uploads """

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request: Request, *args, **kwargs):
        fileSerializer = fileUploadSerializer(data=request.data)
        if fileSerializer.is_valid():
            files = request.FILES.getlist('files')

            # if we pass all checks, store content in db and queue up it up for local ocr and processing
            responses = []
            for file in files:  # we run each file independently, it would be incorrect to assume all files are the same type
                if not allowedFile(file.name):  # basic file type check, doesnt check contents. we do that further downstream
                    responses.append({'filename': file.name, 'error': 'file extension is not allowed'})
                    continue

                # save the content filled with basic details to db
                content = Content()
                content.title = file.name
                content.author = 'iago_vodafone'
                content.file = file
                content.url = content.file.url
                content.type = Content.content_types.pdf
                content.provider = Content.providers.vodafone
                content.save()
                responses.append({'filename': content.title, 'id': content.uuid})

                # send to next step, full ingestion
                threading.Thread(target=ingestContentPDF, name=f'processContentFile_{content.title}', args=[content]).start()

            if all('error' in x for x in responses):
                return Response(responses, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(responses, status=status.HTTP_201_CREATED)
        else:
            return Response(fileSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


class content_via_adjacent_skills(views.APIView):
    """ search for content based on skills """

    def get(self, request: Request):
        return self.post(request)

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.content_via_adjacent_skills)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # required
        query_skills = request.data['skills']
        k: int = request.data['k']
        # optional
        content_type = request.data.get('type')
        length = request.data.get('length')
        page: int = request.data.get('page', 0)

        # start = time.perf_counter()
        skills = [search_fuzzy_cache(Skill, x)[0].first() for x in query_skills]
        skills = [x for x in skills if x]  # remove nones

        # okay now we need to get adjacent skills
        adjacent_skills_dict = []
        adjacent_skills = []
        for skill, skill_name in zip(skills, query_skills):
            if skill is not None:
                # get adjacent skills for our skill
                results, rankings, query_vector = index.skills_index.query(skill.embedding_all_mpnet_base_v2, k=5)
                # unpack the rankings and make a ranked list of pks and a ranked list of scores
                unpacked = list(zip(*rankings))
                skills_ranked = unpacked[0]
                scores_ranked = unpacked[1]

                adjacent_skills_dict.append({'name': skill.name, 'original': skill_name, 'adjacent': skills_ranked[1:], 'scores': scores_ranked[1:]})
                adjacent_skills.extend(skills_ranked[1:])

        # skills tag search
        content_to_return = Content.objects.filter(skills__in=adjacent_skills)

        # apply filters to results_to_return queryset
        # type filter
        if content_type:
            content_to_return = content_to_return.filter(type__in=content_type)

        # length filter
        if length:
            content_to_return = content_to_return.filter(content_read_seconds__lte=length[1], content_read_seconds__gte=length[0])

        # unique filter
        content_to_return = content_to_return.distinct('uuid')

        # perform the transaction
        content_to_return_ids = list(content_to_return.values_list('uuid', flat=True))
        if len(content_to_return_ids) == 0:
            return Response({'response': 'No adjacent skills or related content found', 'content': [], 'adjacent_skills': adjacent_skills_dict}, status=status.HTTP_200_OK)

        # slice the content_to_return_ids list to get the page we want
        content_to_return_ids = content_to_return_ids[page*k:(page+1)*k]

        # determine if we want to return fields or just uuid
        fields = request.data.get('fields')
        if fields:
            content_to_return = Content.objects.filter(uuid__in=content_to_return_ids)
            content_to_return = content_to_return.values(*fields)
            resp = {'content': content_to_return}
        else:
            resp = {'content': content_to_return_ids}

        # add the aux data and respond
        resp['adjacent_skills'] = adjacent_skills_dict
        return Response(resp, status=status.HTTP_200_OK)


class content_via_skills(views.APIView):
    """ Semantic search for content based on skills """
    
    def post(self, request: Request, skill_group: str):
        serializer = serializers.ContentRecommendationBySkillSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Validate skill group
        if skill_group == 'mindtools':
            skill_group_model = MindtoolsSkillGroup
        elif skill_group == 'all':
            skill_group_model = Skill
        else:
            return Response({'response': f'Invalid skill group {skill_group}. Valid: mindtools, all'}, status=status.HTTP_400_BAD_REQUEST)

        # Required
        query_skills: list[str] = serializer.data['skills']
        k: int = serializer.data['k']
        page: int = serializer.data['page']
        fields: list[str] = serializer.data['fields']
        individual_skill_recommendations: bool = serializer.data['individual_skill_recommendations']
        # Optional
        content_type: list | None = serializer.data.get('content_type')
        provider: list | None = serializer.data.get('provider')

        skills = [search_fuzzy_cache(skill_group_model, x, force_result=True)[0].first() for x in query_skills]
        skills = [x for x in skills if x]  # remove nones

        if len(skills) == 0:
            return Response({'response': f'No skills found'}, status=status.HTTP_200_OK)

        if individual_skill_recommendations:
            query_vectors = [(x.name, x.embedding_all_mpnet_base_v2) for x in skills]
        else:
            average = np.mean([x.embedding_all_mpnet_base_v2 for x in skills], axis=0).astype(np.float32)
            query_vectors = [('all_skills', average)]

        # Get semantic search results for each query vector
        results_total = []
        for skill_name, query_vector in query_vectors:
            results, rankings, query_vector = index.content_index.query(query_vector, k=k*(page+1)*10) # multiply by 10 to get more results so that we can hopefully match k results after filtering - not the best solution but fine for now
            # unpack the rankings and make a ranked list of pks and a ranked list of scores
            skills_ranked, scores_ranked = list(zip(*rankings))

            # get the content ids for the ranked skills
            results_to_return = Content.objects.filter(uuid__in=skills_ranked)

            # apply filters to queryset
            if content_type:
                results_to_return = results_to_return.filter(type__in=content_type)
            if provider:
                results_to_return = results_to_return.filter(provider__in=provider)
            results_to_return = results_to_return.distinct('uuid')

            # Perform the transaction and get the fields we want
            results_to_return_data = list(results_to_return.values(*fields))

            # Rank the results by score
            results_to_return_data = sorted(results_to_return_data, key=lambda result: skills_ranked.index(result['pk']))

            # Slice the final list to get the page we want
            results_to_return_data = results_to_return_data[page*k:(page+1)*k]

            # Annotate each with the score
            for result in results_to_return_data:
                result['score'] = scores_ranked[skills_ranked.index(result['pk'])]

            # Add the results to the total results list
            results_total.append({'query': skill_name, 'count': len(results_to_return_data), 'content': results_to_return_data})

        # add the aux data and respond
        resp = {'results': results_total}
        resp['for_humans'] = 'Results genereated via all_mpnet_base_v2 embeddings and FAISS Euclidean Semantic Similarity'
        return Response(resp, status=status.HTTP_200_OK)

class content_via_search(views.APIView):
    """ search for content based on skills """

    def get(self, request: Request):
        return self.post(request)

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.content_via_search)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # required
        k: int = request.data['k']
        # oneOf
        query_string = request.data.get('searchtext')
        query_skills = request.data.get('skills')
        # optional
        content_type = request.data.get('type')
        length = request.data.get('length')
        provider = request.data.get('provider')
        strict = request.data.get('strict', False)
        page: int = request.data.get('page', 0)

        content_to_return = Content.objects.none()

        # if we have a query then we want to search content titles for it
        if query_string:
            results, rankings, query_vector = index.content_index.query(query_string, k=k*(page+2))  # plus 2 instead of 1 cuz im just gonna get extra results to ensure we have enough to ensure k values after filters
            content_to_return |= results

        # otherwise we have skills provided, for each skill in the query, find its closest match in the skills database
        elif query_skills:
            skills = [search_fuzzy_cache(Skill, x)[0] for x in query_skills]
            skills = [x[0] for x in skills if len(x) > 0]  # remove none values

            # skills tag search
            if strict and len(skills) > 0:
                content_to_return |= Content.objects.filter(skills=skills)
            elif len(skills) > 0:
                content_to_return |= Content.objects.filter(skills__in=skills)

        # apply filters to content_to_return queryset

        # type filter
        if content_type:
            content_to_return = content_to_return.filter(type__in=content_type)

        # provider filter
        if provider:
            content_to_return = content_to_return.filter(provider__in=provider)

        # length filter
        if length:
            content_to_return = content_to_return.filter(content_read_seconds__lte=length[1], content_read_seconds__gte=length[0])

        # unique filter
        content_to_return = content_to_return.distinct('uuid')

        # perform the transaction to get all uuids, not limited by k or page because we havent ranked them yet
        content_ids_to_return = list(content_to_return.values_list('uuid', flat=True))
        if len(content_ids_to_return) == 0:
            return Response({'response': 'No matching skills or content titles found', 'content': []}, status=status.HTTP_206_PARTIAL_CONTENT)

        # build a ranked list of the content from the rankings provided by the indexer, which are already ordered by similarity
        if query_string:
            content_ids_to_return_ranked = [x for x, score in rankings if x in content_ids_to_return]  # ensure the result passed our filters
        else:
            content_ids_to_return_ranked = content_ids_to_return

        # slice the content_ids_to_return_ranked list to get the page we want
        content_ids_to_return_ranked = content_ids_to_return_ranked[page*k:(page+1)*k]

        # determine if we want to return fields or just uuid
        fields = request.data.get('fields')
        if fields:
            if not 'pk' in fields:
                fields.append('pk')
            content_to_return = Content.objects.filter(uuid__in=content_ids_to_return_ranked)
            content_to_return = list(content_to_return.values(*fields))
            content_to_return = sorted(content_to_return, key=lambda result: content_ids_to_return_ranked.index(result['pk'])) 
            resp = {'content': content_to_return}
        else:
            resp = {'content': content_ids_to_return_ranked}

        # add the aux data and respond
        if query_skills:
            resp['skills'] = [x.name for x in skills if x is not None]
        return Response(resp, status=status.HTTP_200_OK)


class content_via_recommendation(views.APIView):
    """ generate recommendations for given a job title and content history """

    def get(self, request: Request):
        return self.post(request)

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.content_via_recommendation)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # first match the free-form job title provided to one embedded in our database
        position: str = request.data['position']
        job: Job = search_fuzzy_cache(Job, position, force_result=True)[0].first()
        if job is None:
            return Response({'response': 'No matching job title found'}, status=status.HTTP_400_BAD_REQUEST)

        # next get content objects with the provided content history ids
        content_history: list[Content] = []
        for content_id in request.data['lastconsumedcontent']:
            if is_valid_uuid(content_id):
                try:
                    content = Content.objects.get(uuid=content_id)
                    content_history.append(content)
                except Content.DoesNotExist:
                    return Response({'response': f'Content with UUID {content_id} does not exist', 'content': []}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'response': f'Invalid UUID {content_id}', 'content': []}, status=status.HTTP_400_BAD_REQUEST)

        # we can only generate a content history embedding center if we actually have a history
        if not len(content_history) == 0:
            # now get the center of the content history embeddings
            content_history_vectors = np.array([x.embedding_all_mpnet_base_v2 for x in content_history]).astype(np.float32)
            content_history_center = np.average(content_history_vectors, axis=0)

            # get the weights of job and history and compute the center of the recomendation in the embedding space
            job_weight, history_weight = request.data.get('weights', (1, 1))  # default to equal weights
            recomendation_center = np.average([np.array(job.embedding_all_mpnet_base_v2), content_history_center], axis=0, weights=[job_weight, history_weight])
        else:  # otherwise we can just use the job embedding
            recomendation_center = np.array(job.embedding_all_mpnet_base_v2)

        # now get the closest k content to the recomendation center via our faiss index
        k: int = request.data['k']
        page: int = request.data.get('page', 0)  # default to 0
        temperature = float(request.data.get('temperature', 0)/100)  # default to 0
        p = 10 if temperature == 0 else 1  # if temp is 0 we want to multiply k because it wont get multiplied by p within the query method

        results, rankings, query_vector = index.content_index.query(recomendation_center, k=k*(page+1), min_distance=temperature, truncate_results=False)

        content_to_return = results

        # apply filters
        content_type = request.data.get('type')
        length = request.data.get('length')
        provider = request.data.get('provider')
        # type filter
        if content_type:
            content_to_return = content_to_return.filter(type__in=content_type)

        # length filter
        if length:
            content_to_return = content_to_return.filter(content_read_seconds__lte=length[1], content_read_seconds__gte=length[0])

        # provider filter
        if provider:
            content_to_return = content_to_return.filter(provider__in=provider)

        # unique filter
        content_to_return = content_to_return.distinct('uuid')

        # evaluate the queryset and get the ids
        content_ids_to_return = list(content_to_return.values_list('uuid', flat=True))

        # build a ranked list of the content ids from the rankings provided by the indexer, which are already ordered by similarity to the recomendation center vector
        # ensure the result passed our filters and get the scores for the content ids to return
        content_ids_to_return_ranked, scores = zip(*[(x, score) for x, score in rankings if x in content_ids_to_return])

        # slice the content_ids_to_return_ranked list to get the page we want
        content_ids_to_return_ranked = content_ids_to_return_ranked[page*k:(page+1)*k]

        # determine if we want to return fields or just uuid
        fields = request.data.get('fields')
        if fields: # TODO: validate the fields dynamically, already wrote the code just have to port it here i think its in object search
            if not 'pk' in fields:
                fields.append('pk')
            content_to_return = Content.objects.filter(uuid__in=content_ids_to_return_ranked)
            content_to_return = list(content_to_return.values(*fields))
            content_to_return = sorted(content_to_return, key=lambda result: content_ids_to_return_ranked.index(result['pk']))
            # annotate the content with the score
            for i, content in enumerate(content_to_return):
                content['score'] = scores[i]
            resp = {'content': content_to_return}
        else:
            resp = {'content': content_ids_to_return_ranked}

        # add the aux data and respond
        resp['matched_job'] = job.name
        return Response(resp, status=status.HTTP_200_OK)


class content_via_title(views.APIView):
    """ get content given a content title using fuzzy search """

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.content_via_title)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query: str = request.data.get('query')
        k: int = request.data.get('k')
        page: int = request.data.get('page', 0)  # default to 0

        # get the closest k content to the query via our fuzzy search
        content_to_return, rankings = search_fuzzy_cache(Content, query, k=int(k*(page+1)), force_result=True, search_field='title')

        # apply filters
        content_type = request.data.get('type')
        length = request.data.get('length')
        provider = request.data.get('provider')
        # type filter
        if content_type:
            content_to_return = content_to_return.filter(type__in=content_type)

        # length filter
        if length:
            content_to_return = content_to_return.filter(content_read_seconds__lte=length[1], content_read_seconds__gte=length[0])

        # provider filter
        if provider:
            content_to_return = content_to_return.filter(provider__in=provider)

        # unique filter
        content_to_return = content_to_return.distinct('uuid')

        # evaluate the queryset and get the ids
        content_ids_to_return = list(content_to_return.values_list('uuid', flat=True))

        # build a ranked list of the content ids from the rankings provided by the fuzzy search, which are already ordered by similarity to the query
        content_ids_to_return_ranked = [x for x in rankings if x in content_ids_to_return]  # ensure the result passed our filters

        # slice the content_ids_to_return_ranked list to get the page we want
        content_ids_to_return_ranked = content_ids_to_return_ranked[page*k:(page+1)*k]

        # determine if we want to return fields or just uuid
        fields = request.data.get('fields')
        if fields:
            if not 'pk' in fields:
                fields.append('pk')
            content_to_return = Content.objects.filter(uuid__in=content_ids_to_return_ranked)
            content_to_return = list(content_to_return.values(*fields))
            content_to_return = sorted(content_to_return, key=lambda result: content_ids_to_return_ranked.index(result['pk'])) 
            resp = {'content': content_to_return}
        else:
            resp = {'content': content_ids_to_return_ranked}

        return Response(resp, status=status.HTTP_200_OK)


# * StringEmbedding Views


class stringEmbeddingListAll(views.APIView):
    def get(self, request: Request, model_choice: str):
        # validate and get model
        model_choices_valid = ['topic', 'skill', 'job']
        if model_choice not in model_choices_valid:
            return Response(f'{model_choice} is not a valid model: {model_choices_valid}', status=status.HTTP_404_NOT_FOUND)
        model: models.Model = HUMAN_TO_MODEL[model_choice]

        return Response([str(x) for x in model.objects.all()], status=status.HTTP_200_OK)


class stringEmbeddingCRUD(views.APIView):
    """ CRUD for specified object and instance """

    def get(self, request: Request, model_choice: str, name: str):
        # validate and get model # TODO make this block a function
        model_choices_valid = ['topic', 'skill', 'job']
        if model_choice not in model_choices_valid:
            return Response(f'{model_choice} is not a valid model: {model_choices_valid}', status=status.HTTP_404_NOT_FOUND)
        model: models.Model = HUMAN_TO_MODEL[model_choice]

        if model.objects.filter(name=name).count() > 0:
            return Response(model.objects.filter(name=name).values()[0], status=status.HTTP_200_OK)
        else:
            return Response({'response': f'{model_choice} {name} not found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request: Request, model_choice: str, name: str):
        # validate and get model
        model_choices_valid = ['topic', 'skill', 'job']
        if model_choice not in model_choices_valid:
            return Response(f'{model_choice} is not a valid model: {model_choices_valid}', status=status.HTTP_404_NOT_FOUND)
        model: models.Model = HUMAN_TO_MODEL[model_choice]

        if model.objects.filter(name=name).count() > 0:
            return Response({'response': f'{model_choice} {name} already exists'}, status=status.HTTP_302_FOUND)
        else:
            object = model()
            object.create(name, ai.embedding_model.encode([name])[0])
            object.save()

            if not DEBUG:
                if model == Topic:
                    target = index.topic_index._generate_index()
                elif model == Skill:
                    target = index.skills_index._generate_index()
                elif model == Job:
                    target = index.jobs_index._generate_index()
                threading.Thread(target=target).start()

            return Response({'response': f'{name} created'}, status=status.HTTP_201_CREATED)

    def delete(self, request: Request, model_choice: str, name: str):
        # validate and get model
        model_choices_valid = ['topic', 'skill', 'job']
        if model_choice not in model_choices_valid:
            return Response(f'{model_choice} is not a valid model: {model_choices_valid}', status=status.HTTP_404_NOT_FOUND)
        model: models.Model = HUMAN_TO_MODEL[model_choice]

        if model.objects.filter(name=name).count() > 0:
            model.objects.get(name=name).delete()

            if not DEBUG:
                if model == Topic:
                    target = index.topic_index._generate_index()
                elif model == Skill:
                    target = index.skills_index._generate_index()
                elif model == Job:
                    target = index.jobs_index._generate_index()
                threading.Thread(target=target).start()

            return Response({'response': f'{name} deleted'}, status=status.HTTP_200_OK)
        else:
            return Response({'response': f'{model_choice} {name} not found'}, status=status.HTTP_404_NOT_FOUND)


# * Generic Model Views

class model_field_search(views.APIView):
    """ search for objects """

    def get(self, request: Request, model_choice: str):
        return self.post(request, model_choice)

    def post(self, request: Request, model_choice: str):
        try:
            jsonschema.validate(request.data, schema=schemas_request.model_field_search)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = str(request.data['query'])
        k = int(request.data['k'])
        similarity_minimum = float(request.data.get('similarity_minimum', 30)/100)

        model: models.Model = HUMAN_TO_MODEL[model_choice]
        model_fields = ['pk'] + [x.name for x in model._meta.get_fields()]

        # validate requested return fields
        fields = request.data.get('fields', ['pk'])  # default to just pk returned
        if any(x not in model_fields for x in fields):
            return Response(f'{model_choice} does not have the following fields: {[x for x in fields if x not in model_fields]}', status=status.HTTP_400_BAD_REQUEST)

        # get search field string or default
        search_field = request.data.get('search_field')
        if not search_field:  # defaults are per model
            if model == Content:
                search_field = 'title'
            else:
                search_field = 'name' # ? make this the pk by default?

        # validate search field is in model
        if search_field not in model_fields:
            return Response(f'{model_choice} does not have field: {search_field}', status=status.HTTP_400_BAD_REQUEST)

        # validate search field is of correct type
        if search_field == 'pk':
            search_field_type = type(model._meta.pk)
        else:
            search_field_type = type(model._meta.get_field(search_field))
        if search_field_type not in [models.CharField, models.TextField]:
            return Response(f'{model_choice} field {search_field} is not a string field', status=status.HTTP_400_BAD_REQUEST)

        # perform the search
        results, results_pk = search_fuzzy_cache(model, query, k, similarity_minimum, search_field=search_field)

        # finally get the fields we want
        if fields == ['pk']: # no need to hit the db again if we just want the pks
            results_to_return = results_pk
        elif len(fields) == 1: # return a flat list of values if we only want one field
            results_to_return = results.values_list(fields[0], flat=True)
        else: # otherwise return a list of dicts if we want multiple fields
            results_to_return = results.values(*fields)

        return Response({'results': results_to_return}, status=status.HTTP_200_OK)


# * Utility Views


class transform(views.APIView):
    """ transform texts """
    @extend_schema(responses={200: schemas_response.transform})

    def post(self, request: Request):
        try:
            jsonschema.validate(request.data, schema=schemas_request.texts)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # embed
        embeds = ai.embedding_model.encode(request.data['texts'])

        return Response({'vectors': embeds}, status=status.HTTP_200_OK)


class cache_clear(views.APIView):
    """ clear the cache """

    def delete(self, request: Request):
        cache.clear()
        return Response({'response': 'success'}, status=status.HTTP_200_OK)


class alive(views.APIView):
    """ check if the server is alive """

    def get(self, request: Request):
        return Response('HTTP_209_GOODMORNING', status=status.HTTP_200_OK)
