""" article content pipeline methods """
import json
import logging
import os
from urllib.parse import urlencode

import requests
from django.utils import timezone

from v0.models import Content
from v0.serializers import ContentSerializerWebhook

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
    # resolvedPageUrl is only there if diffbot got redirected
    content.url_response = response['resolvedPageUrl'] if 'resolvedPageUrl' in response else response['pageUrl']
    content.isEnglish = (response['humanLanguage'] == 'en')
    content.isArticle = (response['type'] == 'article')
    content.text = response['text']

    # fin
    content.status = Content.FINISHED
    content.datetime_end = timezone.now()
    content.save()
    return content

def articleCallback(content: Content) -> bool:
    """ posts content data to content webhook """
    payload = ContentSerializerWebhook(content).data
    r = requests.post(str(os.getenv('CONTENT_WEBHOOK_ENDPOINT')), data=payload)
    logger.info(f'got response from Content Webhook: HTTP {r.status_code} {r.text}')

# TODO: do a check once an hour or so ajnd mark all content thats been processing for more than an hour as errored