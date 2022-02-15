import logging

from django.urls import path
from iago.settings import DEBUG
from v0 import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('assistant/msgsforlearner', views.messagesForLearner.as_view(), name='messagesforlearner'),
    path('content/submiturl', views.articleSubmit.as_view(), name='submiturl'),
    path('content/<uuid:id>', views.content.as_view(), name='content-detail'),
    path('content/query', views.querySubmit.as_view()),
    path('skillspace/jobskillmatch', views.jobSkillMatch.as_view()),
    path('topics/', views.topicList.as_view()),
    path('topics/<str:name>', views.topic.as_view()),
]

# this file only runs once so its a good way to do init stuff, maybe not best practice tho 
# TODO: change to https://docs.djangoproject.com/en/3.2/ref/applications/#django.apps.AppConfig.ready
if DEBUG:
    logger.debug('oncedebug')
    from django.contrib.postgres.search import TrigramSimilarity
    from v0.models import Job
    # order by trigram similarity
    # jobs = Job.objects.annotate(similarity=TrigramSimilarity('name', 'aws engineer')).filter(similarity__gt=0.5).order_by('similarity')
    # print(jobs)
    # print('e')
