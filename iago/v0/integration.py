""" integration methods """

import logging
import os

import requests

from v0.models import Content
from v0.serializers import ContentSerializerWebhook

logger = logging.getLogger(__name__)


def articleWebhook(content: Content) -> bool:
    """ posts content data to content webhook """
    
    payload = ContentSerializerWebhook(content).data 
    headers = {'X-KEY': str(os.getenv('CONTENT_WEBHOOK_KEY'))}

    if content.environment == Content.LIVE:
        url = str(os.getenv('CONTENT_WEBHOOK_ENDPOINT_LIVE'))
    else:
        url = str(os.getenv('CONTENT_WEBHOOK_ENDPOINT_TEST'))

    r = requests.post(url, data=payload, headers=headers)
    logger.info(f'got response from Content {str(content.environment).upper()} Webhook: HTTP {r.status_code} {r.text}')

# TODO: do a check once an hour or so ajnd mark all content thats been processing for more than an hour as errored
