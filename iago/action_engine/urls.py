import logging

from django.urls import path
from iago.settings import DEBUG

from action_engine import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('assistant/learner', views.messagesForLearner.as_view(), name='messagesforlearner'),
]

import django
print('testingconn')
print(django.db.connection.ensure_connection())
print('fein')
# this file only runs once so its a good way to do init stuff, maybe not best practice tho
if DEBUG:
    logger.debug('oncedebug')