import json
import os
import threading

import jsonschema
import requests
from iago.permissions import HasGroupPermission
from iago.schemas import messagesForLearnerSchema
from rest_framework import status, views
from rest_framework.response import Response
from action_engine.models import CachedJSON

AIRTABLE_KEY = os.getenv('AIRTABLE_KEY')

def updateCached():
    # get messsages from airtable
    headers = {'Authorization': 'Bearer ' + AIRTABLE_KEY}
    r = requests.get('https://api.airtable.com/v0/appL382zVdInLM23F/Messages?', headers=headers)

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

        # validate data
        try:
            data = json.loads(request.body)
        except ValueError:
            return Response({'status': 'error', 'response': 'request body is not valid JSON'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            jsonschema.validate(data, schema=messagesForLearnerSchema)
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


class aliveView(views.APIView):
    permission_classes = [HasGroupPermission]
    allowed_groups = {
        'GET': ['__all__']
    }

    def get(self, request):
        return Response('alive', status=status.HTTP_200_OK)
