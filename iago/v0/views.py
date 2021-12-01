import json
import os
import threading

import jsonschema
import requests
from iago.permissions import HasGroupPermission
from iago import schemas
from rest_framework import status, views
from rest_framework.response import Response

from v0 import index, utils
from v0.article import articlePipeline
from v0.models import CachedJSON, Content, Topic
from v0.serializers import ContentSerializer, TopicSerializerAll

AIRTABLE_BASE = 'https://api.airtable.com/v0/'
AIRTABLE_KEY = os.getenv('AIRTABLE_KEY')

def updateCached():
    # get messsages from airtable
    headers = {'Authorization': 'Bearer ' + AIRTABLE_KEY}
    r = requests.get(AIRTABLE_BASE+'appL382zVdInLM23F/Messages?', headers=headers)

    airtableMessages, created = CachedJSON.objects.get_or_create(key='AirtableMessages')
    airtableMessages.value = json.loads(r.text)['records']
    airtableMessages.save()

    return {'AirtableMessages': airtableMessages.value}

class messagesForLearner(views.APIView):
    """ take user profile and course data and return applicable messsages """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'POST': ['bubble']
    }

    def post(self, request):
        """ allow update of basic fields, as of now filename type and confidence """

        # validate and load
        if not utils.isValidJSON(request.body):
            return Response({'status': 'error', 'response': 'request body is not valid JSON'}, status=status.HTTP_400_BAD_REQUEST)
        data = json.loads(request.body)

        try:
            jsonschema.validate(data, schema=schemas.messagesForLearnerSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # get messsages from cached airtable if it exists, if it doesnt run the cache update
        messages, created = CachedJSON.objects.get_or_create(key='AirtableMessages')
        if created:
            messages = updateCached()['AirtableMessages']
        else: # no need to wait for airtable if we already have a cached version
            threading.Thread(target=updateCached, name='updateCached').start()
            messages = messages.value # since before we stored the whole object in this var

        # this gets all possible unique locations to send messages from the airtable and converts to snake_case
        locations = set([str(row['fields']['Location']).lower().replace(' ', '_') for row in messages if 'Location' in row['fields']])
        # validate the sent location
        if data['courseData']['location'] not in locations:
            return Response({'status': 'error', 'response': f'location must be one of the following: {locations}'}, status=status.HTTP_400_BAD_REQUEST)

        learnerType = data['userProfile']['learner_type']
        possibles = []

        for row in messages:
            # filter the messages so that we only get one relevant to our current position and learner type
            if 'Learner type' in row['fields'] and (learnerType in row['fields']['Learner type'] or 'Everyone' in row['fields']['Learner type']) and str(row['fields']['Location']).lower().replace(' ', '_') == data['courseData']['location']:
                possibles.append(row)

        return Response({'messages': possibles}, status=status.HTTP_200_OK)

class articleSubmit(views.APIView):
    """ submit an article to the pipeline """
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'POST': ['bubble']
    }

    def post(self, request):
        # validate and load
        if not utils.isValidJSON(request.body):
            return Response({'status': 'error', 'response': 'request body is not valid JSON'}, status=status.HTTP_400_BAD_REQUEST)
        data = json.loads(request.body)

        try:
            jsonschema.validate(data, schema=schemas.articleSubmissionSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        # we have now passed validation. time to fill the initial content object and pass it to the pipeline methods
        content = Content()
        content.url_submitted = data['url']
        if 'environment' in data: # if we have the environment specified store it, default to test
            content.environment = Content.LIVE if data['environment'] == 'live' else Content.TEST
        content.save()

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
        if not utils.isValidJSON(request.body):
            return Response({'status': 'error', 'response': 'request body is not valid JSON'}, status=status.HTTP_400_BAD_REQUEST)
        data = json.loads(request.body)

        try:
            jsonschema.validate(data, schema=schemas.querySubmissionSchema)
        except jsonschema.exceptions.ValidationError as err:
            return Response({'status': 'error', 'response': err.message, 'schema': err.schema}, status=status.HTTP_400_BAD_REQUEST)

        k = data['k'] if 'k' in data else 5

        inference, vector =  index.content_index.query(data['query'], k=k)

        neu_inferences = []
        for content, probability in inference: # iterate through our inferences list and structure the data so that its easy for humans to analyze
            structured_topic = {
                'name': str(content), # name of the topic
                'url': str(content.url_response), # url of the content
                'probability': probability # probablity of the topic being correct for the input text
            }
            neu_inferences.append(structured_topic)

        return Response({'inference': neu_inferences}, status=status.HTTP_200_OK)

# model based views

class content(views.APIView):
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['bubble']
    }

    def get(self, request, id):
        if Content.objects.filter(id=id).count() > 0:
            return Response(ContentSerializer(Content.objects.get(id=id), context={'request': request}).data, status=status.HTTP_200_OK)
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
