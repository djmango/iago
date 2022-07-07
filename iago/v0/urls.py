import logging

from django.urls import path
from iago.settings import DEBUG, LOGGING_LEVEL_MODULE

from v0 import views

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)

urlpatterns = [
    path('index/query', views.queryIndex.as_view()),
    path('models/autocomplete', views.modelAutocomplete.as_view()),
    path('content/update', views.updateContent.as_view()),
    path('content/search', views.searchContent.as_view()),
    path('content/recommend', views.recommendContent.as_view()),
    path('content/adjacent_to_skills', views.adjacentSkillContent.as_view()),
    path('content/upload', views.contentFileUploadView.as_view()),
    path('skillspace/jobskillmatch', views.jobSkillMatch.as_view()),
    path('skillspace/adjacent', views.adjacentSkills.as_view()),
    path('skillspace/match', views.matchSkills.as_view()),
    path('skillspace/match_embeds', views.matchSkillsEmbeds.as_view()),
    path('topics/', views.topicList.as_view()),
    path('transform/', views.transform.as_view()),
    path('topics/<str:name>', views.topic.as_view()),
]

# this file only runs once so its a good way to do init stuff, maybe not best practice tho 
# TODO: change to https://docs.djangoproject.com/en/3.2/ref/applications/#django.apps.AppConfig.ready
if DEBUG:
    logger.debug('i am the onceler')
    logger.debug('i am the twiceler')
