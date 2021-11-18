""" article content pipeline methods """
import json
import logging
import os
import threading
from urllib.parse import urlencode

import numpy as np
import requests
from django.utils import timezone
from iago.settings import TOPIC_MODEL_NAME

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

    # topic analysis
    # this try is just temporary
    if content.isEnglish and content.isArticle: # only if english article for now
        topic_model = ai.loadModel(TOPIC_MODEL_NAME)
        topic_model.calculate_probabilities = True
        inference = topic_model.transform(content.text)

        # isolate calculated probabilities and rank them
        probabilities = inference[1][0]
        # rank in descending order
        probabilities_ranked = np.flip(inference[1][0][np.argsort(probabilities)])

        # get topic ids from probabilities by matching values to original model output
        topic_ids = list([int(np.where(probabilities==val)[0]) for val in probabilities_ranked[:10]]) # wow hdbscan broke

        # retrieve topic data with our ids
        inferences_nolabel = [topic_model.get_topic(id) for id in topic_ids]
        content.topic = inferences_nolabel[0][0][0]

        # structure top inference data for human analysis
        content.inferences[TOPIC_MODEL_NAME] = []
        for i, topic in enumerate(inferences_nolabel): # iterate through our inferences list and structure the data so that its easy for humans to analyze
            structured_topic = {'name': topic[0][0], # highest importance scoring word in the topic
            'probability': probabilities_ranked[i], # probablity of the topic being correct for the input text
            'human_representation': [{'word': word[0], 'importance': word[1]} for word in topic]} # essentially just name the word-importance pairs for easy reading
            content.inferences[TOPIC_MODEL_NAME].append(structured_topic)

    # fin
    content.status = Content.FINISHED
    content.datetime_end = timezone.now()
    content.save()

    elapsed = divmod((content.datetime_end - content.datetime_start).total_seconds(), 60) # get tuple of mins and secs elapsed
    logger.info(f'finished {content.title} in {round(elapsed[0])}m {round(elapsed[1], 2)}s')
    threading.Thread(target=articleWebhook, name=f'articleWebhook_{content.id}', args=[content]).start()

    return content
