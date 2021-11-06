import logging

from django.urls import path
from iago.settings import DEBUG

from v0 import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('assistant/msgsforlearner', views.messagesForLearner.as_view(), name='messagesforlearner'),
    path('content/submiturl', views.articleSubmit.as_view(), name='submiturl')
]

# this file only runs once so its a good way to do init stuff, maybe not best practice tho 
# TODO: change to https://docs.djangoproject.com/en/3.2/ref/applications/#django.apps.AppConfig.ready
if DEBUG:
    logger.debug('oncedebug')

    from v0.article import articleCallback
    from v0.models import Content

    # articleCallback(Content.objects.get(id='612a9a9f-3a32-4024-9cbd-3abcf72e298e'))
    # https://webhook.site/#!/6e943ff0-d75f-4915-99b2-fac610096af2/b5c76679-28e4-4ea6-abfb-51ec1c9c88bd/1

    # from top2vec import Top2Vec
    # from v0.models import Article

    # logger.debug('loading topic training data')
    # data = list(Article.objects.all().values_list('content', flat=True))
    # logger.debug('topic data loaded, training')

    # # model = Top2Vec(documents=data, embedding_model='universal-sentence-encoder', workers=8)
    # model = Top2Vec(documents=data, embedding_model='doc2vec', speed='learn', workers=8)

    # model.save('topicmodeldoc2vecBIG.t2v')

    # print(model)

    # delete stuff
    # from langdetect import detect

    # articles = Article.objects.all()

    # for article in articles:
    #     if len(article.content) < 50 or detect(article.content) != 'en':
    #         article.delete()
    #         print('deleted')