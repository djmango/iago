""" article content pipeline methods """
import json
import logging
import os
import threading
from urllib.parse import urlencode

import requests
from django.utils import timezone

import v0.ai as ai
from v0.integration import articleWebhook
from v0.models import Content

logger = logging.getLogger(__name__)

DIFFBOT_BASE = 'https://api.diffbot.com/v3/'
DIFFBOT_KEY = os.getenv('DIFFBOT_KEY')

def articlePipeline(content: Content) -> Content:
    
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
    if 'objects' not in response or len(response['objects']) == 0:
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

    # topic analysis and embeding
    if content.isEnglish and content.isArticle: # only if english article for now
        content.topic, content.inferences[ai.topic_model.model_name] = ai.topic_model.inferenceTopic(content.text)
        content.embeddings[ai.topic_model.embedding_model_name] = ai.topic_model.encode([content.text])[0].tolist()

    # fin
    content.status = Content.FINISHED
    content.datetime_end = timezone.now()
    content.save()

    elapsed = divmod((content.datetime_end - content.datetime_start).total_seconds(), 60) # get tuple of mins and secs elapsed
    logger.info(f'finished {content.title} in {round(elapsed[0])}m {round(elapsed[1], 2)}s')
    threading.Thread(target=articleWebhook, name=f'articleWebhook_{content.id}', args=[content]).start()

    return content
