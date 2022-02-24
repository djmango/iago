import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)


def load(name, max_seq_length):
  """ loads HuggingFace SentenceTransformer model, sets options, and saves to disc """
  try:
    model = SentenceTransformer(name, device='cpu') # keeping on cpu for now since we dont batch
    model.max_seq_length = max_seq_length
    model.save(str(HERE/'models'/name), model_name=name, create_model_card=False)
  except Exception as e:
    raise(e)

load('all-mpnet-base-v2', max_seq_length=384)
