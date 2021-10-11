import requests
import os
import json
from urllib.parse import urlencode

AIRTABLE_KEY = os.getenv('AIRTABLE_KEY')

headers = {'Authorization': 'Bearer ' + AIRTABLE_KEY}
r = requests.get('https://api.airtable.com/v0/app5RXbed7Bn4wO2g/Messages?', headers=headers)
messages = json.loads(r.text)['records']

learnerType = 'IXMC'
possibles = []

for row in messages:
    if learnerType in row['fields']['Learner type']:
        possibles.append(row)

print(possibles)