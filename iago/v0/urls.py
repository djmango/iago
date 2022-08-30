import logging

from django.urls import path
from iago.settings import DEBUG, LOGGING_LEVEL_MODULE

from v0 import views

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)

urlpatterns = [
    path('cache/clear', views.cache_clear.as_view()),
    path('content/adjacent_to_skills', views.content_via_adjacent_skills.as_view()),
    path('content/recommend', views.content_via_recommendation.as_view()),
    path('content/mindtools_skill', views.content_via_mindtools_skills.as_view()),
    path('content/search', views.content_via_search.as_view()),
    path('content/update', views.content_update.as_view()),
    path('content/search_title', views.content_via_title.as_view()),
    path('content/upload', views.content_file_upload.as_view()),
    path('index/<str:index_choice>/query', views.index_query.as_view()),
    path('index/<str:index_choice>/rebuild', views.index_rebuild.as_view()),
    path('objects/<str:model_choice>/all', views.stringEmbeddingListAll.as_view()),
    path('objects/<str:model_choice>/search', views.model_field_search.as_view()),
    path('objects/<str:model_choice>/<str:name>', views.stringEmbeddingCRUD.as_view()),
    path('skills/adjacent', views.skills_adjacent.as_view()),
    path('skills/match_embeds', views.skills_match_embeds.as_view()),
    path('skills/match', views.skills_match.as_view()),
    path('transform/', views.transform.as_view()),
    # ! deprecated
    path('skillspace/match_embeds', views.skills_match_embeds.as_view()),
    path('skillspace/adjacent', views.skills_adjacent.as_view()),
    path('skillspace/match', views.skills_match.as_view()),
]
