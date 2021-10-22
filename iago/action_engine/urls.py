import logging

from django.urls import path
from iago.settings import DEBUG

from action_engine import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('assistant/msgsforlearner', views.messagesForLearner.as_view(), name='messagesforlearner'),
]

# this file only runs once so its a good way to do init stuff, maybe not best practice tho 
# TODO: change to https://docs.djangoproject.com/en/3.2/ref/applications/#django.apps.AppConfig.ready
if DEBUG:
    logger.debug('oncedebug')
    # from top2vec import Top2Vec
    # from action_engine.models import Article

    # logger.debug('loading topic training data')
    # data = list(Article.objects.all().values_list('content', flat=True))
    # logger.debug('topic data loaded, training')

    # # model = Top2Vec(documents=data, embedding_model='universal-sentence-encoder', workers=32)
    # model = Top2Vec(documents=data, embedding_model='doc2vec', speed='learn', workers=32)

    # model.save('topicmodeldoc2vec.t2v')

    # print(model)

    # delete stuff
    # from langdetect import detect

    # articles = Article.objects.all()

    # for article in articles:
    #     if len(article.content) < 50 or detect(article.content) != 'en':
    #         article.delete()
    #         print('deleted')