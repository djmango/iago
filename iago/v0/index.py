import logging
import time
from pathlib import Path
from typing import Iterable

import faiss
import numpy as np
from django.db.models.query import QuerySet
from iago.settings import DEBUG
from sentence_transformers import util

from v0.ai import embedding_model
from v0.models import Content, Skill, Topic

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
        self.d = 768
        self._generate_index()

    def _generate_index(self):
        """ generate the index using the literable """
        start = time.perf_counter()
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.d))  # dimensions of vectors

        # either get or generate vectors
        if type(self.iterable) == QuerySet:
            self.vectors = np.array(list(self.iterable.values_list('embedding_all_mpnet_base_v2', flat=True))).astype(np.float32)
        else:
            self.vectors = self.embedding_model.encode(self.iterable).astype(np.float32)

        self.index.add_with_ids(self.vectors, np.array(range(0, len(self.vectors))).astype(np.int64))
        self.logger.info(f'Generated index with a total of {self.index.ntotal} vectors in {round(time.perf_counter()-start, 4)}s')


    def _min_distance(self, indices: list, min_distance: float):
        """ Find closest k matches with a minimum distance between matches for a given index, assumes vector is of same embedding model as the index

        Args:
            indices (list): List if index values of the embeddings to ensure min_distance between
            min_distance (float,): Minimum distance between embeddings. Ranges from 0 to 1, 0 returning all results and 1 returning none.

        Returns:
            results list(Tuple(Topic_id, similarity)): List of tuples, object from self.queryset and its similarity to the query_vector, in descending order
        """

        start = time.perf_counter()
        # get actual vectors of the results
        # https://www.pinecone.io/learn/faiss-tutorial/
        # we have k vectors to return - so we initialize a zero array to hold them
        vectors = np.array([self.vectors[x] for x in indices[0]])

        # Compute cosine-similarities for each vector with each other vector
        # https://www.sbert.net/docs/usage/semantic_textual_similarity.html
        cosine_scores = np.array(util.cos_sim(vectors, vectors))

        # get the indices of the vectors that are outside the min_distance
        results_to_remove = set()
        for i, vector_results in enumerate(cosine_scores):
            for j, result in enumerate(vector_results):
                if i not in results_to_remove and j not in results_to_remove and i != j and 1-result < min_distance : # don't compare to self, and dont compare to already removed results
                    results_to_remove.add(j)

        # get indices in the global index of the results we want to keep
        cleaned_indices = [int(x) for i, x in enumerate(indices[0]) if i not in results_to_remove]
        self.logger.info(f'Performed min_dist and got {len(cleaned_indices)} vectors in {round(time.perf_counter()-start, 4)}s')

        return cleaned_indices

    def query(self, query: str, k: int = 1, min_distance: float = 0.0):
        """ Find closest k matches for a given query using semantic embedding_model

        Args:
            query (str): The string to find closest matches for
            k (int, optional): Number of results to return. Defaults to 1.
            min_distance (float, optional): Minimum distance between matches. Ranges from 0 to 1, 0 returning all results and 1 returning none. Defaults to 0.

        Returns:
            results: list(Tuple(Model, similarity)): List of tuples, object from self.queryset and its similarity to the query, in descending order
            queryVector (np.ndarray): embedding of the submitted query
        """
        
        start = time.perf_counter()
        query_vector = self.embedding_model.encode([query])

        if min_distance > 0: # if we want to filter results then we must get extra results initially to satisfy k
            p = 10
        else:
            p = 1

        values, indices = self.index.search(query_vector, k*p)
        self.logger.info(f'Searched index and got {len(values[0])} vectors in {round(time.perf_counter()-start, 4)}s')

        # figure out if we need to run min_distance or not, do so if necessary, and get a list of results
        if min_distance > 0:
            cleaned_indices = self._min_distance(indices, min_distance)
            results = [(self.iterable[indice], value) for value, indice in zip(values.tolist()[0], cleaned_indices)]
        else:
            results = [(self.iterable[indice], value) for value, indice in zip(values.tolist()[0], indices.tolist()[0])]  # 0 because query_vector is a list of 1 element
        
        return results[:k], query_vector[0]

    def query_vector(self, query_vector: np.ndarray, k: int = 1, min_distance: float = 0.0):
        """ Find closest k matches for a given index, assumes vector is of same embedding model as the index

        Args:
            vector (ndarray): The vector to find closest matches for.
            k (int, optional): Number of results to return. Defaults to 1.
            min_distance: (float, optional): Minimum distance between matches. Ranges from 0 to 1, 0 returning all results and 1 returning none. Defaults to 0.

        Returns:
            results: list(Tuple(Model, similarity)): List of tuples, object from self.queryset and its similarity to the query_vector, in descending order
        """

        start = time.perf_counter()
        query_vector = np.array([query_vector]).astype(np.float32)

        if min_distance > 0: # if we want to filter results then we must get extra results initially to satisfy k
            p = 10
        else:
            p = 1

        values, indices = self.index.search(query_vector, k*p)
        self.logger.info(f'Searched index and got {len(values[0])} vectors in {round(time.perf_counter()-start, 4)}s')

        # figure out if we need to run min_distance or not, do so if necessary, and get a list of results
        if min_distance > 0:
            cleaned_indices = self._min_distance(indices, min_distance)
            results = [(self.iterable[indice], value) for value, indice in zip(values.tolist()[0], cleaned_indices)]
        else:
            results = [(self.iterable[indice], value) for value, indice in zip(values.tolist()[0], indices.tolist()[0])]  # 0 because query_vector is a list of 1 element
        
        return results[:k]

topic_index: VectorIndex
content_index: VectorIndex
skills_index: VectorIndex
if not DEBUG or False: # set to true to enable indexes in debug
    topic_index = VectorIndex(Topic.objects.all())
    content_index = VectorIndex(Content.objects.exclude(embedding_all_mpnet_base_v2__isnull=True))
    skills_index = VectorIndex(Skill.objects.all())
