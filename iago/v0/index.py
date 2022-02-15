import logging
import time
from pathlib import Path
from typing import Iterable

import faiss
import numpy as np
from django.db.models.query import QuerySet

from v0.ai import embedding_model
from v0.models import Content, Topic, Skill

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)


class VectorIndex():
    """ Index class for semantic embedding and implementing vector search """
    embedding_model = embedding_model.model

    def __init__(self, iterable: Iterable):
        self.iterable = iterable
        if type(iterable) == QuerySet:
            self.logger = logging.getLogger(f'VectorIndex_{self.iterable.model.__name__}')
        else:
            self.logger = logging.getLogger(f'VectorIndex_Iterable')
        self.generate_index()

    def generate_index(self):
        """ generate the index using the literable """
        start = time.perf_counter()
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(768))  # dimensions of vectors

        # either get or generate vectors
        if type(self.iterable) == QuerySet:
            vectors = np.array(self.iterable.values_list('embedding_all_mpnet_base_v2', flat=True)).astype(np.float32)
        else:
            vectors = self.embedding_model.encode(self.iterable).astype(np.float32)

        self.index.add_with_ids(vectors, np.array(range(0, len(vectors))).astype(np.int64))
        self.logger.info(f'Generated index with a total of {self.index.ntotal} vectors in {round(time.perf_counter()-start, 4)}s')

    def query(self, query: str, k: int = 1):
        """ Find closest k matches for a given query using semantic embedding_model

        Args:
            query (str): The string to inference topic of
            k (int, optional): Number of results to return. Defaults to 1.

        Returns:
            results list(Tuple(Topic_id, similarity)): List of tuples, object from self.queryset and its similarity to the query, in descending order
            queryVector (np.ndarray): embedding of the submitted query
        """

        query_vector = self.embedding_model.encode([query])
        values, indices = self.index.search(query_vector, k)
        query_vector = query_vector[0]

        results = [(self.iterable[indice], value) for value, indice in zip(values.tolist()[0], indices.tolist()[0])]  # 0 because query_vector is a list of 1 element
        return results, query_vector

    def query_vector(self, query_vector: np.ndarray, k: int = 1):
        """ Find closest k matches for a given index, assumes vector is of same embedding model as the index

        Args:
            vector (ndarray): The vector to find closest matches for
            k (int, optional): Number of results to return. Defaults to 1.

        Returns:
            results list(Tuple(Topic_id, similarity)): List of tuples, object from self.queryset and its similarity to the query_vector, in descending order
        """

        query_vector = np.array([query_vector]).astype(np.float32)
        values, indices = self.index.search(query_vector, k)

        results = [(self.iterable[indice], value) for value, indice in zip(values.tolist()[0], indices.tolist()[0])]  # 0 because query_vector is a list of 1 element
        return results


topic_index = VectorIndex(Topic.objects.all())
content_index = VectorIndex(Content.objects.exclude(embedding_all_mpnet_base_v2__isnull=True))
skills_index = VectorIndex(Skill.objects.all())
