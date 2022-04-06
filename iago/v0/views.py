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
from v0.models import Job, ScrapedArticle, Skill, Topic
from v0.serializers import TopicSerializerAll

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
            skills: list[Skill] = index.skills_index.query_vector(embed, k=10, min_distance=.21) # NOTE these are hardcoded for now, important params if you want to change results

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
            skills: list[Skill] = index.skills_index.query_vector(embed, k=10, min_distance=.21) # NOTE these are hardcoded for now, important params if you want to change results

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


class transformScrapedArticles(views.APIView):
    """ transform all scraped articles and saves the embeddings """
    permission_classes = [HasGroupPermission]
    allowed_groups = {}

    def get(self, request):
        # get all articles with no embeddings
        start = time.perf_counter()
        articles: list[ScrapedArticle] = list(ScrapedArticle.objects.filter(embedding_all_mpnet_base_v2__isnull=True))

        # start transforming in a thread
        threading.Thread(target=transformArticles, name=f'transformArticles_{len(articles)}', args=[articles]).start()
        return Response({'status': 'started', 'count': len(articles), 'time': round(time.perf_counter()-start, 3)}, status=status.HTTP_200_OK)


def updateArticle(article_uuid):
    """ seperate function for job pooling """
    start = time.perf_counter()

    article: ScrapedArticle = ScrapedArticle.objects.get(uuid=article_uuid)

    postID = article.url.split('/')[-1].split('-')[-1]
    r = requests.get(f'https://medium.com/_/api/posts/{postID}')
    data = json.loads(r.text[16:])
    post = data['payload']['value']
    logger.info(f'Call took {time.perf_counter()-start:.3f}s')

    skills: list[Skill] = index.skills_index.query_vector(article.embedding_all_mpnet_base_v2, k=10, min_distance=.21)

    for skill, similarity in skills:
        article.skills.add(skill)

    article.popularity['medium'] = {'totalClapCount': post['virtuals']['totalClapCount']}

    article.updated_on = Now()
    article.save()
    logger.info(f'Updated {article.title} in {time.perf_counter()-start:.3f}s')


def updateScrapedArticles():
    """ update scraped articles with their medium data """

    start = time.perf_counter()
    articles_uuid = list(ScrapedArticle.objects.all().values_list('uuid', flat=True))
    logger.info(f'Getting articles took {time.perf_counter()-start:.3f}s')
    logger.info(f'Updating data for {len(articles_uuid)} articles')

    p = ThreadPool(processes=20)
    p.map(updateArticle, articles_uuid)
    p.close()


class skillSearch(views.APIView):
    permission_classes = [HasGroupPermission]

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.queryKSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        query = str(request.data['query'])
        k = int(request.data['k'])

        skills = Skill.objects.annotate(similarity=TrigramSimilarity('name', query)).filter(similarity__gt=0.3).order_by('-similarity')
        return Response({'skills': [str(x.name) for x in skills][:k]}, status=status.HTTP_200_OK)


class contentSkillSearch(views.APIView):
    """ search for content based on skills """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['express_api']
    }

    def get(self, request):
        try:
            jsonschema.validate(request.data, schema=schemas.contentSkillsSearchSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        strict = request.data['strict'] if 'strict' in request.data else False

        start = time.perf_counter()
        skills = []
        # for each skill in the query, find its closest match in the skills database
        for skill_name in request.data['skills']:
            skill = Skill.objects.annotate(similarity=TrigramSimilarity('name', skill_name)).filter(similarity__gt=0.7).order_by('-similarity').first()
            if skill is not None:
                skills.append(skill)
        logger.info(f'Skill search took {round(time.perf_counter() - start, 3)}s')

        if len(skills) == 0:
            return Response({'WILL_WRITE_ERROR_LATER_NO_FOUND_SKILLS': []}, status=status.HTTP_200_OK)

        # search content based on the skills
        start = time.perf_counter()
        if strict:
            content = list(ScrapedArticle.objects.filter(skills=skills).values('uuid', 'title', 'url', 'skills', 'thumbnail', 'popularity', 'updated_on'))
        else:
            content = list(ScrapedArticle.objects.filter(skills__in=skills).values('uuid', 'title', 'url', 'skills', 'thumbnail', 'popularity', 'updated_on'))
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
