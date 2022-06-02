import logging

from django.urls import path
from iago.settings import DEBUG
from v0 import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('index/query', views.queryIndex.as_view()),
    path('content/update', views.updateContent.as_view()),
    path('content/search', views.searchContent.as_view()),
    path('content/recommend', views.recomendContent.as_view()),
    path('skillspace/jobskillmatch', views.jobSkillMatch.as_view()),
    path('skillspace/search', views.searchSkills.as_view()),
    path('skillspace/adjacent', views.adjacentSkills.as_view()),
    path('skillspace/match', views.matchSkills.as_view()),
    path('skillspace/match_embeds', views.matchSkillsEmbeds.as_view()),
    path('topics/', views.topicList.as_view()),
    path('transform/', views.transform.as_view()),
    path('transformarticles/', views.transformContents.as_view()),
    path('topics/<str:name>', views.topic.as_view()),
]

# this file only runs once so its a good way to do init stuff, maybe not best practice tho 
# TODO: change to https://docs.djangoproject.com/en/3.2/ref/applications/#django.apps.AppConfig.ready
if DEBUG:
    logger.debug('oncedebug')

    # from v0.models import SkillCluster, Skill
    # from sentence_transformers import util
    # import numpy as np
    # import time

    # SkillCluster.objects.all().delete()
    # skills = list(Skill.objects.all())

    # print("Start clustering")

    # # community detection

    # # Two parameters to tune:
    # # min_cluster_size: Only consider cluster that have at least 10 elements
    # # threshold: Consider sentence pairs with a cosine-similarity larger than threshold as similar
    # start = time.perf_counter()
    # clusters = util.community_detection(np.array([x.embedding_all_mpnet_base_v2 for x in skills]), min_community_size=5, threshold=0.75)
    # print(f'Created {len(clusters)} clusters in {round(time.perf_counter()-start, 3)}s')


    # # Print for all clusters the top 3 and bottom 3 elements
    # start = time.perf_counter()
    # for cluster in clusters:
    #     skillcluster = SkillCluster()
    #     skillcluster.k_top = skills[cluster[0]]
    #     skillcluster.save()
    #     for skill_id in cluster:
    #         skills[skill_id].cluster = skillcluster
    #         skills[skill_id].save()
    #     print('Finished ' + str(skillcluster.id))
    # print(f'Wrote clusters to db in {round(time.perf_counter()-start, 3)}s')

    # start = time.perf_counter()
    # Skill.objects.bulk_update(skills, ['cluster'])
    # print(f'Bulk updated in {round(time.perf_counter()-start, 3)}s')