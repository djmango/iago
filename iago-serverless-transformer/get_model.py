import logging
from pathlib import Path

from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)

# Load model from HuggingFace Hub
tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-mpnet-base-v2')
model = AutoModel.from_pretrained('sentence-transformers/all-mpnet-base-v2')

tokenizer.save_pretrained(HERE/'models'/'all-mpnet-base-v2_tokenizer')
model.save_pretrained(HERE/'models'/'all-mpnet-base-v2_model')
