import logging
import time
from pathlib import Path

import faiss
import numpy as np

from v0.ai import embedding_model
from v0.models import Content, Topic

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)

class QuerysetVectorIndex():
    """ Queryset inference class for using existing embeddings and implementing vector search, and other methods """

    def __init__(self, queryset):
        self.embedding_model = embedding_model.model
        self.queryset = queryset
        self.logger = logging.getLogger(f'QuerysetVectorIndex_{self.queryset.model.__name__}')
        self.generate_index()

    def generate_index(self):
        start = time.perf_counter()
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(768)) # dimensions of vectors
        vectors = np.array(self.queryset.values_list('embedding_all_mpnet_base_v2', flat=True)).astype(np.float32)
        self.index.add_with_ids(vectors, np.array(range(0, len(vectors))).astype(np.int64))
        self.logger.info(f'Generated index with a total of {self.index.ntotal} vectors in {round(time.perf_counter()-start, 4)}s')

    # NOTE this breaks if you delete content and then regenerate the index, no need to fix right now since generating is quick
    # def update_index(self):
    #     """ use queryset to generate index """
    #     vectors = np.array(self.queryset.values_list('embedding_all_mpnet_base_v2', flat=True)).astype(np.float32)[self.index.ntotal:] # slice by ntotal so we dont add existing vectors, works since order is preserved
    #     self.index.add_with_ids(vectors, np.array(range(self.index.ntotal, len(vectors)+self.index.ntotal)).astype(np.int64))

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

        results = [(self.queryset[indice], value) for value, indice in zip(values.tolist()[0], indices.tolist()[0])] # 0 because query_vector is a list of 1 element
        return results, query_vector

topic_index = QuerysetVectorIndex(Topic.objects.all())
content_index = QuerysetVectorIndex(Content.objects.exclude(embedding_all_mpnet_base_v2__isnull=True))
