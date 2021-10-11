import json
import os

import jsonschema
import requests
from iago.permissions import HasGroupPermission
from iago.schemas import messagesForLearnerSchema
from rest_framework import status, views
from rest_framework.response import Response

AIRTABLE_KEY = os.getenv('AIRTABLE_KEY')

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

        # get messsages from airtable
        headers = {'Authorization': 'Bearer ' + AIRTABLE_KEY}
        r = requests.get('https://api.airtable.com/v0/app5RXbed7Bn4wO2g/Messages?', headers=headers)
        messages = json.loads(r.text)['records']

        learnerType = data['userProfile']['learner_type_option_learner_type']
        possibles = []

        for row in messages:
            if learnerType in row['fields']['Learner type']:
                possibles.append(row)

        return Response({'messages': possibles}, status=status.HTTP_200_OK)
