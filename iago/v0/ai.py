""" methods and init related to ai and ml models """
import logging
import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)

os.makedirs(HERE/'models', exist_ok=True)

class Model():
    """ simple handler for sentence_transformers models """
    def __init__(self, name: str, max_seq_length: int = 384):
        self.name = name
        self.max_seq_length = max_seq_length
        self.model: SentenceTransformer
        self.load()

    def load(self):
        """ loads model """
        self.model = SentenceTransformer(self.name, cache_folder=HERE/'models', device='cpu') # keeping on cpu for now since we dont batch
        self.model.max_seq_length = self.max_seq_length

# define embedding model
embedding_model = Model('all-mpnet-base-v2')
