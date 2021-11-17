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

    # # from v0.models import Article
    # from bertopic import BERTopic
    # import hdbscan
    # import random
    # import json
    # import os
    # os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    # # https://github.com/MaartenGr/BERTopic/issues/65
    # clusterer = hdbscan.HDBSCAN(min_cluster_size=50, prediction_data=True, cluster_selection_method='eom')
    
    # logger.info('loading topic training data')
    # # data = list(Article.objects.all().values_list('content', flat=True))
    # # with open('content.json', 'w') as f:
    # #     f.write(json.dumps(data))
    # with open('content.json', 'r') as f:
    #     data = json.loads(f.read())
    # random.shuffle(data)
    # data = data[:100000]

    # logger.info(f'topic data loaded, training with {len(data)}')

    # # topic_model = BERTopic(verbose=True)
    # topic_model = BERTopic(nr_topics='auto', verbose=True, calculate_probabilities=True, hdbscan_model=clusterer)
    # topics, probs = topic_model.fit_transform(data)
    # logger.info('done training topic SAVING')
    # topic_model.save('topic_v0.2')
    # logger.info('saved')
    # logger.info('saving probs')
    # with open('probs.json', 'w') as f:
    #     f.write(json.dumps(probs))
    # logger.info('saved')

# cpu is c4a.8xlarge
# gpu is g4ad.2xlarge