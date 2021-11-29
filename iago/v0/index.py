import logging
from pathlib import Path

import faiss
import numpy as np

from v0.ai import embedding_model
from v0.models import Topic

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)

class TopicInference():
    """ Topic inference method using existing topic embeddings and vector search """

    def __init__(self):
        self.embedding_model = embedding_model
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(768)) # dimensions of vectors
        self.topics = Topic.objects.all()

        vectors = np.array(self.topics.values_list('embedding_all_mpnet_base_v2', flat=True)).astype(np.float32)
        self.index.add_with_ids(vectors, np.array(range(0, len(self.topics))).astype(np.int64))

    def query(self, query: str, k: int = 1):
        """[summary]

        Args:
            query (str): The string to inference topic of
            k (int, optional): Number of results to return. Defaults to 1.

        Returns:
            list Tuple(Topic_id, similarity): List of tuples, pair of Topic object id (its name) and their similarity to the query, in descending order
        """

        query_vector = self.embedding_model.encode([query])
        values, indices = self.index.search(query_vector, k)

        results = []
        for value, indice in zip(values.tolist()[0], indices.tolist()[0]): # 0 because query_vector is a list of 1 element
            results.append((str(self.topics[indice]), value))
        # result = [self.topics[i] for i in indices.tolist()[0]]
        return results

topic_inference = TopicInference()
