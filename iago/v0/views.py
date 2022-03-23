import json
import logging
import os
import re
import threading
import time

import jsonschema
import numpy as np
import requests
from django.contrib.postgres.search import TrigramSimilarity
from iago.permissions import HasGroupPermission
from rest_framework import status, views
from rest_framework.response import Response

from v0 import index, schemas, ai
from v0.article import articlePipeline
from v0.models import CachedJSON, Content, Job, ScrapedArticle, Topic
from v0.serializers import ContentSerializer, TopicSerializerAll

AIRTABLE_BASE = 'https://api.airtable.com/v0/'
AIRTABLE_KEY = os.getenv('AIRTABLE_KEY')

logger = logging.getLogger(__name__)


def updateCached():
    # get messsages from airtable
    headers = {'Authorization': 'Bearer ' + AIRTABLE_KEY}
    r = requests.get(AIRTABLE_BASE+'appL382zVdInLM23F/Messages?', headers=headers)

    airtableMessages, created = CachedJSON.objects.get_or_create(key='AirtableMessages')
    airtableMessages.value = json.loads(r.text)['records']
    airtableMessages.save()

    return {'AirtableMessages': airtableMessages.value}

class articleSubmit(views.APIView):
    """ submit an article to the pipeline """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'POST': ['bubble']
    }

    def post(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.articleSubmissionSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # we have now passed validation. time to fill the initial content object and pass it to the pipeline methods
        content = Content()
        content.url_submitted = request.data['url']
        if 'environment' in request.data:  # if we have the environment specified store it, default to test
            content.environment = Content.LIVE if request.data['environment'] == 'live' else Content.TEST
        content.save()

        if 'sync' in request.data and request.data['sync']:
            content = articlePipeline(content)
            return Response(ContentSerializer(content).data, status=status.HTTP_200_OK)
        else:
            # pass to pipeline methods, pipeline is basically just defined here riht now, will build something more structured once we have decided architecture
            threading.Thread(target=articlePipeline, name=f'articlePipeline_{content.id}', args=[content]).start()
            return Response({'content_id': content.id}, status=status.HTTP_201_CREATED)


class querySubmit(views.APIView):
    """ get related articles to the submitted query """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'POST': ['bubble']
    }

    def post(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.querySubmissionSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = request.data['query']
        k = request.data['k'] if 'k' in request.data else 5

        if 'text' not in request.data:  # query our database of content
            inference, vector = index.content_index.query(query, k=k)

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
            # texts = ['']
            # i = 0
            # for word in data['text'].split('. '):
            #     # bump to next text boundary if we are above 50 words
            #     if utils.words_in(texts[i]) > 50:
            #         texts[i] = texts[i].strip()
            #         i += 1
            #         texts.append('')
            #     # concat to current segment
            #     texts[i] += str(word) + ' '

            # we will just split by sentences for now
            # texts = data['text'].split('. ')
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
            jsonschema.validate(request.data, schema=schemas.transformSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # embed
        vectors = ai.embedding_model.model.encode(request.data['texts'])

        return Response({'vectors': vectors}, status=status.HTTP_200_OK)


class transformScrapedArticles(views.APIView):
    """ transform all scraped articles and saves the embeddings """
    permission_classes = [HasGroupPermission]
    allowed_groups = {}

    def get(self, request):
        # get all articles with no embeddings
        start = time.perf_counter()
        articles: list[ScrapedArticle] = list(ScrapedArticle.objects.filter(embedding_all_mpnet_base_v2__isnull=True))
        # get their contents and embed them
        contents = [x.content for x in articles]
        logger.info(f'generating vectors for {len(articles)}')
        vectors = ai.embedding_model.model.encode(contents, show_progress_bar=True)

        # update the queryset articles with the new embeddings
        logger.info('saving vectors..')
        for article, vector in zip(articles, vectors):
            article.embedding_all_mpnet_base_v2 = vector.tolist()
            article.save()
        
        # bulk save
        # ScrapedArticle.objects.bulk_update(articles, ['embedding_all_mpnet_base_v2'])
        return Response({'status': 'good stuff', 'count': len(articles), 'time': round(time.perf_counter()-start, 3)}, status=status.HTTP_200_OK)


class jobSkillMatch(views.APIView):
    """ take a job title string and return matching skills """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'POST': ['bubble']
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


# model based views


class content(views.APIView):
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['bubble']
    }

    def get(self, request, id):
        if Content.objects.filter(id=id).count() > 0:
            return Response(ContentSerializer(Content.objects.get(id=id)).data, status=status.HTTP_200_OK)
        else:
            return Response({'error': f'{id} not found'}, status=status.HTTP_404_NOT_FOUND)


# Topic CRUD class views

class topicList(views.APIView):
    def get(self, request):
        return Response([str(topic) for topic in Topic.objects.all()], status=status.HTTP_200_OK)


class topic(views.APIView):
    """ CRUD for specified topic """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['bubble']
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
