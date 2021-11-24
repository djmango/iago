""" methods and init related to ai and ml models """
import logging
import os
import time
from pathlib import Path
from typing import Iterable, List
import numpy as np
from sentence_transformers import SentenceTransformer

import boto3
from bertopic import BERTopic
from iago.settings import DEBUG, TOPIC_MODEL_NAME

HERE = Path(__file__).parent

class TopicModel():
    """
    Class to handle all methods relating to a topic model
    Includes embedding methods and embedder
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.logger = logging.getLogger(self.model_name)
        self.embedding_model_name = 'all-mpnet-base-v2'
        self.model_path = HERE/'models'/self.model_name
        self.loadModel()

    def loadModel(self, force: bool = False):
        """ Loads specified model into memory, as well as sentence embedding model

        Args:
            model_name (str): Specified model to load, if not downloaded, will be pulled from s3
        """

        if not self.model_path.exists(): # ensure we have it downloaded
            self.downloadModel(self.model_name)

        if force or not hasattr(self, 'topic_model'):
            start = time.perf_counter()

            # the embedding model becomes a child of topic_model
            embedding_model = SentenceTransformer(self.embedding_model_name)
            embedding_model.max_seq_length = 384
            self.logger.info(f'embedding input sequence limited at {embedding_model.max_seq_length} tokens')
            self.topic_model: BERTopic = BERTopic.load(self.model_path, embedding_model=embedding_model)
            self.logger.info(f'Loaded {self.model_name} in {round(time.perf_counter()-start, 3)}s') # print name and time taken

    def downloadModel(self, force: bool = False) -> bool:
        """ Downloads specified model into filesystem, and calls the load method

        Args:
            model_name (str): Specified model to download
            force (bool, optional): Force a download even if file already exists. Defaults to False.
        Returns:
            bool: If the model was downloaded
        """

        if force or not self.model_path.exists(): # ensure we have it downloaded
            start = time.perf_counter()
            os.makedirs(HERE/'models', exist_ok=True)
            s3 = boto3.client('s3', aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID') , aws_secret_access_key=os.getenv('AWS_ACCESS_KEY_SECRET'))
            s3.download_file('iago-bucket', f'models/{self.model_name}', str(self.model_path))
            self.logger.info(f'Downloaded {self.model_name} in {round(time.perf_counter()-start, 3)}s') # print name and time taken
        
        self.loadModel(self.model_name)

        return force or not self.model_path.exists()

    def inferenceTopic(self, text: str, result_count: int = 10):
        """ Takes input text and returns topic model inference of most likely topics

        Args:
            text (str): text to inference
            result_count (int): the number of results in descending order of probability to return

        Returns:
            top_topic: string of most representitive word of the inferenced most likely topic
            inferences: list of top result_count topics in human readable format
        """                                

        self.topic_model.calculate_probabilities = True
        inference = self.topic_model.transform(text)

        # isolate calculated probabilities and rank them
        probabilities = inference[1][0]
        # rank in descending order
        probabilities_ranked = np.flip(inference[1][0][np.argsort(probabilities)])

        # get topic ids from probabilities by matching values to original model output
        topic_ids = list([int(np.where(probabilities==val)[0]) for val in probabilities_ranked[:result_count]])

        # retrieve topic data with our ids
        inferences_nolabel = [self.topic_model.get_topic(id) for id in topic_ids]
        top_topic = inferences_nolabel[0][0][0]

        # structure top inference data for human analysis
        inferences = []
        for i, topic in enumerate(inferences_nolabel): # iterate through our inferences list and structure the data so that its easy for humans to analyze
            structured_topic = {'name': topic[0][0], # highest importance scoring word in the topic
            'probability': probabilities_ranked[i], # probablity of the topic being correct for the input text
            'human_representation': [{'word': word[0], 'importance': word[1]} for word in topic]} # essentially just name the word-importance pairs for easy reading
            inferences.append(structured_topic)

        return top_topic, inferences

    def encode(self, input: List[str]):
        embeddings = self.topic_model.embedding_model.embed(input, verbose=True)
        return embeddings


topic_model = TopicModel(TOPIC_MODEL_NAME)
