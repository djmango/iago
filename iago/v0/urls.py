import logging

from django.urls import path
from iago.settings import DEBUG
from v0 import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('content/<uuid:id>', views.content.as_view(), name='content-detail'),
    path('content/query', views.querySubmit.as_view()),
    path('skillspace/jobskillmatch', views.jobSkillMatch.as_view()),
    path('topics/', views.topicList.as_view()),
    path('transform/', views.transform.as_view()),
    path('transformarticles/', views.transformScrapedArticles.as_view()),
    path('topics/<str:name>', views.topic.as_view()),
]

# this file only runs once so its a good way to do init stuff, maybe not best practice tho 
# TODO: change to https://docs.djangoproject.com/en/3.2/ref/applications/#django.apps.AppConfig.ready
if DEBUG:
    logger.debug('oncedebug')
    # from v0.index import skills_index

    # skills_index.query_min_distance('massage therapist', k=10, min_distance=.1)
    # skills_index.query_min_distance('massage therapist', k=10, min_distance=.2)
    # skills_index.query_min_distance('massage therapist', k=10, min_distance=.3)
    # skills_index.query_min_distance('massage therapist', k=10, min_distance=.4)
    # skills_index.query_min_distance('massage therapist', k=10, min_distance=.5)