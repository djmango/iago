import logging
import time
from pathlib import Path

import faiss
import numpy as np
from django.core.cache import cache
from django.db.models import Q
from django.db.models.query import QuerySet
from iago.settings import DEBUG
from sentence_transformers import util

from v0.ai import embedding_model
from v0.models import Content, Skill, Topic, UnsplashPhoto
from v0.utils import get_hash

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)


class VectorIndex():
    """ Index class for semantic embedding and implementing vector search """

    def __init__(self, iterable: QuerySet):
        self.iterable = iterable
        if type(iterable) == QuerySet:
            self.logger = logging.getLogger(f'v0.VectorIndex_{self.iterable.model.__name__}')
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
            # https://stackoverflow.com/questions/7558908/unpacking-a-list-tuple-of-pairs-into-two-lists-tuples
            self.pks, self.vectors = zip(*list(self.iterable.values_list('pk', 'embedding_all_mpnet_base_v2')))
            self.vectors = np.array(self.vectors).astype(np.float32)
        else:
            raise ValueError('VectorIndex supported for non-queryset iterables is deprecated')

        self.index.add_with_ids(self.vectors, np.array(range(0, len(self.vectors))).astype(np.int64))
        self.logger.info(f'Generated index with a total of {self.index.ntotal} vectors in {round(time.perf_counter()-start, 4)}s')

    def _generate_cache_key(self, vector: np.ndarray, k: int, min_distance: float):
        """ Generate a unique string to given a vector and k """
        hashed_vector = get_hash(vector.tolist())
        return f'queryvector_{hashed_vector.hex()}_k{str(k)}_md{str(min_distance)}'

    def _min_distance(self, indices: list[int], min_distance: float):
        """ Returns the indices that are a provided minimum semantic distance from each other in a given list of indices

        Args:
            indices (list): List of index values of the embeddings to ensure min_distance between
            min_distance (float,): Minimum distance between embeddings. Ranges from 0 to 1, 0 returning all results and 1 returning none.

        Returns:
            results list([int]): List of indexes that are outside the min_distance
            results_to_remove set([int]): Set of index values (i) that got removed from incides
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
        # self.logger.debug(f'Performed min_dist and got {len(cleaned_indices)} vectors in {round(time.perf_counter()-start, 4)}s')

        return cleaned_indices, results_to_remove

    def query(self, query: str | list | np.ndarray, k: int = 1, min_distance: float = 0.0, use_cached=True, truncate_results=True):
        """ Find closest k matches for a given query or vector using semantic embedding_model

        Args:
            query (str, list, np.ndarray): The string or embedding vector to find closest matches for
            k (int, optional): Number of results to return. Defaults to 1.
            min_distance (float, optional): Minimum distance between matches. Ranges from 0 to 1, 0 returning all results and 1 returning none. Defaults to 0.
            use_cached (bool, optional): Whether to use the cached vectors or not. Defaults to True.
            truncate_results (bool, optional): Whether to truncate the results to the top k. Defaults to True.

        Returns:
            results: (QuerySet): List of tuples, object from self.iterable and its similarity to the query, in descending order or a queryset
            rankings: (list): List of tuples, pk and similarity to the query pairs, in descending order
            query_vector (np.ndarray): embedding of the submitted query if a query is a str instead of an np.ndarray
        """
        
        start = time.perf_counter()

        if type(query) == str:
            query_vector = embedding_model.encode([query]).astype(np.float32)
        elif type(query) == np.ndarray:
            query_vector = np.array([query]).astype(np.float32)
        elif type(query) == list:
            if len(query) != self.d:
                raise ValueError(f'Query vector must be of length {self.d}')
            query_vector = np.array([query]).astype(np.float32)
        else:
            raise ValueError('Query must be a str, list, or np.ndarray')

        if min_distance > 0: # if we want to filter results then we must get extra results initially to satisfy k
            p = 10
        else:
            p = 1

        # generate a unique deterministic string to cache the results
        if use_cached:
            cache_key = self._generate_cache_key(query_vector, k*p, min_distance)
            # self.logger.debug(f'Hashed vector in {round(time.perf_counter()-start, 4)}s')
            cached_results = cache.get(cache_key)

        if use_cached and cached_results:  # if we got results just depickle them
            cleaned_values, cleaned_indices = cached_results
        else:  # if not in cache, run the search and cache the results
            values, indices = self.index.search(query_vector, k*p)
            # figure out if we need to run min_distance or not, do so if necessary, and get a list of results
            if min_distance > 0:
                # so for clarity, cleaned indices is a list of i values corresponding to our parent iterable, our queryset, where results_to_remove is a list of i values that got removed from indices, which can be confusing because there are two lists of indices, one being the parent of the other essentially
                cleaned_indices, results_to_remove = self._min_distance(indices, min_distance)
                # we need to keep values in the same order as cleaned_indices, so remove the values corresponding to the indices we removed
                cleaned_values = [value for i, value in enumerate(values.tolist()[0]) if i not in results_to_remove]
            else:
                cleaned_indices = indices.tolist()[0] # 0 because query_vector is a list of 1 element
                cleaned_values = values.tolist()[0]
            # store the results as a tuple of np.ndarrays, with the row index and its value (ranking) to be able to depickle and order easily later
            if use_cached:
                cache.set(cache_key, (cleaned_values, cleaned_indices), timeout=60*60*24*2)  # 2 day timeout

        # truncate to k results since we might have expanded them if we used min_distance
        if truncate_results:
            cleaned_indices = cleaned_indices[:k]
            cleaned_values = cleaned_values[:k]
        
        # the iterable could be sliced to ensure that we are using a new queryset to filter the results
        results: QuerySet = self.iterable.model.objects.filter(pk__in=[self.pks[x] for x in cleaned_indices])
        rankings = [(self.pks[indice], value) for indice, value in zip(cleaned_indices, cleaned_values)]
        return results, rankings, query_vector

topic_index: VectorIndex
skills_index: VectorIndex
content_index: VectorIndex
unsplash_photo_index: VectorIndex
vodafone_index: VectorIndex
if not DEBUG or False: # set to true to enable indexes in debug
    topic_index = VectorIndex(Topic.objects.all())
    unsplash_photo_index = VectorIndex(UnsplashPhoto.objects.exclude(embedding_all_mpnet_base_v2__isnull=True)[:30000])
    skills_index = VectorIndex(Skill.objects.all())
    # index only content that has more than 200 likes - supposedly the  best 10% of content according to the numbers in our db
    content_index = VectorIndex(Content.objects.exclude(embedding_all_mpnet_base_v2__isnull=True).filter(~Q(provider='medium') | (Q(provider='medium') & Q(popularity__medium__totalClapCount__gt=200))))
    vodafone_index = VectorIndex(Content.objects.exclude(embedding_all_mpnet_base_v2__isnull=True).filter(provider='vodafone'))
