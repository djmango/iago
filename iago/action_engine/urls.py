import logging

from django.urls import path
from iago.settings import DEBUG

from action_engine import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('assistant/learner', views.messagesForLearner.as_view(), name='messagesforlearner'),
]

# this file only runs once so its a good way to do init stuff, maybe not best practice tho
if DEBUG:
    logger.debug('oncedebug')