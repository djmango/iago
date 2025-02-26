import logging
import time
from pathlib import Path

import faiss
import numpy as np
from django.core.cache import cache
from django.db.models import Model, Q
from django.db.models.query import QuerySet
from iago.settings import DEBUG, MODEL_VECTOR_SIZE
from pathos.threading import ThreadPool
from sentence_transformers import util

from v0.ai import embedding_model
from v0.models import Content, Job, MindtoolsSkillGroup, MindtoolsSkillSubgroup, Skill, Topic, UnsplashPhoto
from v0.utils import generate_cache_key

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)


class VectorIndex():
    """ Index class for semantic embedding and implementing vector search """

    def __init__(self, queryset: QuerySet, generate_index=True):
        assert isinstance(queryset, QuerySet), 'VectorIndex only supports QuerySets'
        self.queryset = queryset
        self.model: Model = self.queryset.model
        self.logger = logging.getLogger(f'v0.VectorIndex_{self.queryset.model.__name__}')
        self.d = MODEL_VECTOR_SIZE
        if generate_index:
            self._generate_index()

    def _generate_index(self):
        """ Generate the FAISS IndexIDMap using the QuerySet """
        start = time.perf_counter()
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.d))  # dimensions of vectors

        # get vectors from the QuerySet
        self.pks, self.vectors = zip(*list(self.queryset.values_list('pk', 'embedding_all_mpnet_base_v2')))
        self.vectors = np.array(self.vectors).astype(np.float32)

        # add vectors to the index
        self.index.add_with_ids(self.vectors, np.array(range(0, len(self.vectors))).astype(np.int64))
        self.logger.info(f'Generated index for {self.queryset.model.__name__} with a total of {self.index.ntotal} vectors in {round(time.perf_counter()-start, 4)}s')

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
                if i not in results_to_remove and j not in results_to_remove and i != j and 1-result < min_distance:  # don't compare to self, and dont compare to already removed results
                    results_to_remove.add(j)

        # get indices in the global index of the results we want to keep
        cleaned_indices = [int(x) for i, x in enumerate(indices[0]) if i not in results_to_remove]
        # self.logger.debug(f'Performed min_dist and got {len(cleaned_indices)} vectors in {round(time.perf_counter()-start, 4)}s')

        return cleaned_indices, results_to_remove

    def query(self, query: str | list[float] | np.ndarray, k: int = 1, min_distance: float = 0.0, use_cached=True, truncate_results=True):
        """ Find closest k matches for a given query or vector using semantic embedding_model

        Args:
            query (str | list[float] | np.ndarray): The string, list of strings, or embed vector to find closest matches for
            k (int, optional): Number of results to return. Defaults to 1.
            min_distance (float, optional): Minimum distance between matches. Ranges from 0 to 1, 0 returning all results and 1 returning none. Defaults to 0.
            use_cached (bool, optional): Whether to use the cached vectors or not. Defaults to True.
            truncate_results (bool, optional): Whether to truncate the results to the top k. Defaults to True.

        Returns:
            results: (QuerySet): List of tuples, object from self.queryset and its similarity to the query, in descending order or a queryset.
            rankings: (list): List of tuples, pk and similarity to the query pairs, in descending order.
            query_vector (np.ndarray): embedding of the submitted query if a query is a str instead of an np.ndarray.
        """

        if not hasattr(self, 'index'):
            logger.info(f'Index not generated for {self.queryset.model.__name__}, generating..')
            self._generate_index()

        # For redundancy, just to make sure the index truly did get generated
        assert self.index is not None, 'Index not generated'

        if type(query) == str:
            query_vector = embedding_model.encode([query]).astype(np.float32)
        # TODO: make this method able to handle multiple queries or make a new method for backwards compat
        # elif type(query) == list and all(type(x) == str for x in query):
        #     query_vector = embedding_model.encode(query).astype(np.float32)
        elif type(query) == np.ndarray:
            query_vector = np.array([query]).astype(np.float32)
        elif type(query) == list and all(type(x) == float for x in query):
            if len(query) != self.d:
                raise ValueError(f'Query vector must be of length {self.d}')
            query_vector = np.array([query]).astype(np.float32)
        else:
            raise ValueError('Query must be a str, list[float], or np.ndarray')

        assert np.isfinite(query_vector).all(), "Query vector contains NaN or Inf"

        if min_distance > 0:  # if we want to filter results then we must get extra results initially to satisfy k
            p = 10
        else:
            p = 1

        # generate a unique deterministic string to cache the results
        if use_cached: # It's important to include all the params that affect the results, otherwise we could cache incorrect results
            cache_key = generate_cache_key(query_vector.tolist(), str(self.queryset.query), k*p, min_distance, version=2)
            cached_results = cache.get(cache_key)

        if use_cached and cached_results:  # if we got results unpack them
            cleaned_values, cleaned_indices = cached_results
        else:  # if not in cache, run the search and cache the results
            values, indices = self.index.search(query_vector, k*p)
            # figure out if we need to run min_distance or not, do so if necessary, and get a list of results
            if min_distance > 0:
                # so for clarity, cleaned indices is a list of i values corresponding to our parent queryset, our queryset, where results_to_remove is a list of i values that got removed from indices, which can be confusing because there are two lists of indices, one being the parent of the other essentially
                cleaned_indices, results_to_remove = self._min_distance(indices, min_distance)
                # we need to keep values in the same order as cleaned_indices, so remove the values corresponding to the indices we removed
                cleaned_values = [value for i, value in enumerate(values.tolist()[0]) if i not in results_to_remove]
            else:
                cleaned_indices = indices.tolist()[0]  # 0 because query_vector is a list of 1 element
                cleaned_values = values.tolist()[0]
            # store the results as a tuple of np.ndarrays, with the row index and its value (ranking) to be able to depickle and order easily later
            if use_cached:
                cache.set(cache_key, (cleaned_values, cleaned_indices), timeout=60*60*24*2)  # 2 day timeout

        # truncate to k results since we might have expanded them if we used min_distance
        if truncate_results:
            cleaned_indices = cleaned_indices[:k]
            cleaned_values = cleaned_values[:k]

        # the queryset could be sliced to ensure that we are using a new queryset to filter the results
        results: QuerySet = self.queryset.model.objects.filter(pk__in=[self.pks[x] for x in cleaned_indices if x != -1]) # -1 is the value returned when there is no match because k is out of index bounds
        rankings = [(self.pks[indice], value) for indice, value in zip(cleaned_indices, cleaned_values)]
        return results, rankings, query_vector


# decleare VectorIndexes as global so we can access them throughout the app
topic_index: VectorIndex
skills_index: VectorIndex
content_index: VectorIndex
unsplash_photo_index: VectorIndex
vodafone_index: VectorIndex
jobs_index: VectorIndex
mindtools_skillgroup_index: VectorIndex
mindtools_skillsubgroup_index: VectorIndex

def init_indexes(multithreaded=True):
    """ 
    Initialize the VectorIndexes for each model in parrallel
    Each index is initiated by a QuerySet, some have filters, each QuerySet's model is a child of StringEmbedding
    """
    logger.info('Initializing indexes..')
    start = time.perf_counter()

    # we are updating the declared global indexes
    global content_index
    global topic_index
    global jobs_index
    global unsplash_photo_index
    global vodafone_index
    global skills_index
    global mindtools_skillgroup_index
    global mindtools_skillsubgroup_index

    # Define the indexes but do not run the indexing yet
    content_index = VectorIndex(Content.objects.exclude(embedding_all_mpnet_base_v2__isnull=True).filter(~Q(provider='medium') | (Q(provider='medium') & Q(popularity__medium__totalClapCount__gt=200))), not multithreaded)  # index only content that has more than 200 likes - supposedly the  best 10% of content according to the numbers in our db
    topic_index = VectorIndex(Topic.objects.all(), not multithreaded)
    jobs_index = VectorIndex(Job.objects.all(), not multithreaded)
    unsplash_photo_index = VectorIndex(UnsplashPhoto.objects.exclude(embedding_all_mpnet_base_v2__isnull=True)[:30000], not multithreaded)  # index only the first 30000 unsplash photos
    vodafone_index = VectorIndex(Content.objects.exclude(embedding_all_mpnet_base_v2__isnull=True).filter(provider='vodafone'), not multithreaded)  # index only vodafone content for demo purposes
    skills_index = VectorIndex(Skill.objects.all(), False)
    mindtools_skillgroup_index = VectorIndex(MindtoolsSkillGroup.objects.all(), False)
    mindtools_skillsubgroup_index = VectorIndex(MindtoolsSkillSubgroup.objects.all(), False)

    # Build lists so that we can initialize the indexes in parallel. Debug mode has a different list to make sure we only load what we need to debug, as this takes quite some time.
    if not DEBUG:
        indexes_to_build = [content_index, topic_index, jobs_index, unsplash_photo_index, vodafone_index, skills_index, mindtools_skillgroup_index, mindtools_skillsubgroup_index]
    else:
        indexes_to_build = []

    # build the indexes in parallel
    logger.info(f'{len(indexes_to_build)} indexes specified to be built at startup.')
    if len(indexes_to_build) == 0:
        return
    elif multithreaded:
        with ThreadPool(processes=3) as pool:
            pool.map(lambda x: x._generate_index(), indexes_to_build)
    logger.info(f'Indexes initialized in {time.perf_counter()-start:.3f}s!')


def ready():
    """ This function is called when the app is ready to be used. """
    init_indexes(multithreaded=True)
