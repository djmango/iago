import logging

from django.urls import path
from iago.settings import DEBUG

from v0 import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('assistant/msgsforlearner', views.messagesForLearner.as_view(), name='messagesforlearner'),
    path('content/submiturl', views.articleSubmit.as_view(), name='submiturl'),
    path('content/<uuid:id>', views.content.as_view(), name='content-detail'),
]

# this file only runs once so its a good way to do init stuff, maybe not best practice tho 
# TODO: change to https://docs.djangoproject.com/en/3.2/ref/applications/#django.apps.AppConfig.ready
if DEBUG:
    logger.debug('oncedebug')

    # from v0.index import topic_inference

    # e = topic_inference.query('i want to learn about economics', k=5)
    # print(e)
