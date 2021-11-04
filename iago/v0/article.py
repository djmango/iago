""" article content pipeline methods """
import json
import logging
import os
from urllib.parse import urlencode

import requests
from django.utils import timezone

from v0.models import Content

logger = logging.getLogger(__name__)

DIFFBOT_BASE = 'https://api.diffbot.com/v3/'
DIFFBOT_KEY = os.getenv('DIFFBOT_KEY')

def articleDiffbotSubmit(content: Content) -> Content:
    
    # record our status
    content.status = Content.PROCESSING
    content.save()

    # send the request to diffbot
    params = urlencode({
        'token': DIFFBOT_KEY,
        'url': content.url_submitted,
        'discussion': False, # we dont want article comments
    })
    r = requests.get(DIFFBOT_BASE+'article?'+params)
    response = json.loads(r.text)

    # check we actually got a valid response
    if len(response['objects']) == 0:
        logger.error(f'{content.id} RETURNED NO OBJECTS FROM DIFFBOT {content.url_submitted}')
        content.status = Content.ERRORED
        content.save()
        return content
    else:
        response = response['objects'][0]

    # fill in our object with the details from diffbot
    content.diffbot_response = response
    content.title = response['title']
    content.url_response = response['pageUrl']
    content.isEnglish = (response['humanLanguage'] == 'en')
    content.isArticle = (response['type'] == 'article')
    content.text = response['text']

    # fin
    content.status = Content.FINISHED
    content.datetime_end = timezone.now()
    content.save()
    return content

def articleCallback(content: Content) -> bool:
    """ posts data from document assosited with given ID to onder app

        Args:
            id (UUID4): id of document to send to onder app

        Returns:
            bool of success
    """
    return False
    # TODO: build serializer for this

    # get advanced data
    # a = dict()
    # # send request
    # url = str(os.getenv('WEBHOOK_ENDPOINT'))+'/api/property-documents/ml-update?='

    # payload=f'id={document.id}&type={document.type}&additionalData={dict}'.encode('utf-8')
    # headers = {
    # 'Content-Type': 'application/x-www-form-urlencoded'
    # }

    # response = requests.request("POST", url, headers=headers, data=payload, auth=(os.getenv('WEBHOOK_USER'), os.getenv('WEBHOOK_PASS')))
    # logger.info(f'got response fron App: HTTP {response.status_code} {response.text}')
