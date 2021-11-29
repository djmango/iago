""" methods and init related to ai and ml models """
import logging
import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = 'all-mpnet-base-v2'

# define embedding model
os.makedirs(HERE/'models', exist_ok=True)
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, cache_folder=HERE/'models')
embedding_model.max_seq_length = 384
