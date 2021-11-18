""" methods and init related to ai and ml models """
import logging
import os
import time
from pathlib import Path
from sentence_transformers import SentenceTransformer

import boto3
from bertopic import BERTopic
from iago.settings import DEBUG, TOPIC_MODEL_NAME

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)

topic_model = None

def loadModel(model_name: str, force: bool = False) -> BERTopic:
    """ Loads specified model into memory

    Args:
        model_name (str): Specified model to load, if not downloaded, will be pulled from s3
    Returns:
        BERTopic: Model instance
    """
    model_path = HERE/'models'/model_name

    if not model_path.exists(): # ensure we have it downloaded
        downloadModel(model_name)

    # load into global
    global topic_model
    if force or topic_model is None:
        start = time.perf_counter()

        embedding_model = SentenceTransformer('all-distilroberta-v1')
        embedding_model.max_seq_length = 512
        logger.info(f'embedding input sequence limited at {embedding_model.max_seq_length} tokens')

        topic_model = BERTopic.load(model_path, embedding_model=embedding_model)
        logger.info(f'Loaded {model_name} in {round(time.perf_counter()-start, 3)}s') # print name and time taken

    return topic_model

def downloadModel(model_name: str, force: bool = False) -> bool:
    """ Downloads specified model into filesystem

    Args:
        model_name (str): Specified model to download
        force (bool, optional): Force a download even if file already exists. Defaults to False.
    Returns:
        bool: If the model was downloaded
    """
    model_path = HERE/'models'/model_name

    if force or not model_path.exists(): # ensure we have it downloaded
        start = time.perf_counter()
        os.makedirs(HERE/'models', exist_ok=True)
        s3 = boto3.client('s3', aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID') , aws_secret_access_key=os.getenv('AWS_ACCESS_KEY_SECRET'))
        s3.download_file('iago-bucket', f'models/{model_name}', str(model_path))
        logger.info(f'Downloaded {model_name} in {round(time.perf_counter()-start, 3)}s') # print name and time taken
    loadModel(model_name)

    return force or not model_path.exists()

# init this to save time on first call in prod, in debug i dont want to have it load every single time
if not DEBUG:
    downloadModel(TOPIC_MODEL_NAME)
