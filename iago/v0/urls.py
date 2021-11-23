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

    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    import hdbscan
    import random
    import json
    import os
    import pickle
    from scipy import sparse
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    # https://github.com/MaartenGr/BERTopic/issues/65
    # https://github.com/scikit-learn-contrib/hdbscan/pull/495
    
    # # custom algo instances
    # clusterer = hdbscan.HDBSCAN(min_cluster_size=10, metric='euclidean', prediction_data=True, cluster_selection_method='eom', core_dist_n_jobs=8)
    # embedding_model = SentenceTransformer('all-distilroberta-v1')
    # embedding_model.max_seq_length = 512
    # logger.info(f'embedding input sequence limited at {embedding_model.max_seq_length} tokens')
    
    # # logger.info('loading topic training data')
    # # with open('content.json', 'r') as f:
    # #     sentences = json.loads(f.read())
    # # random.shuffle(sentences)
    # # sentences = sentences[:100000]

    # # logger.info(f'topic data loaded, training with {len(sentences)}')

    # # # embed, this is expensive
    # # embeddings = embedding_model.encode(sentences, show_progress_bar=True, normalize_embeddings=True)

    # # # save embeddings
    # # with open('embeddings.pkl', "wb") as f:
    # #     pickle.dump({'sentences': sentences, 'embeddings': embeddings}, f, protocol=pickle.HIGHEST_PROTOCOL)
    # # logger.info('saved embeddings')

    # # Load sentences & embeddings from disc
    # with open('embeddings_roberta_100k.pkl', "rb") as f:
    #     stored_data = pickle.load(f)
    #     sentences = stored_data['sentences']
    #     embeddings = stored_data['embeddings']
    # logger.info(f'embed data loaded, training with {len(sentences)}')

    # # topic modeling
    # topic_model = BERTopic(nr_topics='auto', verbose=True, n_gram_range=(1,2), calculate_probabilities=False, embedding_model=embedding_model, hdbscan_model=clusterer)
    # topic_model.fit(sentences, embeddings=embeddings)
    # logger.info('done training topic SAVING')
    # topic_model.save('topic_v0.6', save_embedding_model=False)
    # logger.info('saved')

# cpu is c4a.8xlarge
# gpu is g4ad.2xlarge