""" methods and init related to ai and ml models """
import logging
import os
import time
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from v0.models import GenericStringEmbedding

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)

os.makedirs(HERE/'models', exist_ok=True)

class Model():
    """ simple handler for sentence_transformers models """
    def __init__(self, name: str, max_seq_length: int):
        self.name = name
        self.max_seq_length = max_seq_length
        self.model: SentenceTransformer
        self.load()

    def load(self):
        """ loads model """
        self.model = SentenceTransformer(self.name, cache_folder=HERE/'models')
        self.model.max_seq_length = self.max_seq_length

    def encode(self, strings: list[str], use_cache=True, show_progress_bar=False):
        """ gets embeds from strings from cache if availablbe, else embeds strings and saves to cache and returns"""
        start = time.perf_counter()

        # first get what we can from cache and build a list of ones we still need to embed
        if use_cache:
            strings = [s.lower() for s in strings]
            cache = list(GenericStringEmbedding.objects.filter(name__in=strings))
            cached_strings = [x.name for x in cache] # so we know what we have
            uncached_strings = [x for x in strings if x not in cached_strings]
            logger.info(f'Embedder got {len(cached_strings)}/{len(strings)} from cache in {time.perf_counter()-start:.3f}s')
        else:
            uncached_strings = strings

        # next embed the ones we still need and save to cache
        new_cache = []
        if not use_cache or len(uncached_strings) > 0:
            new_embeds = self.model.encode(uncached_strings, show_progress_bar=show_progress_bar)
            for i, string in enumerate(uncached_strings):
                new_cache.append(GenericStringEmbedding().create(string, new_embeds[i]))

            GenericStringEmbedding.objects.bulk_create(new_cache)
            logger.info(f'Finished embedding and saved to cache in {time.perf_counter()-start:.3f}s')

        # finally, join the cached and new, order by original param, and return
        joined = cache + new_cache
        joined_strings = [x.name for x in joined]
        results = []
        for string in strings:
            i = joined_strings.index(string)
            results.append(joined[i].embedding_all_mpnet_base_v2)

        return np.asarray(results)

# define embedding model
embedding_model = Model('all-mpnet-base-v2', max_seq_length=384)
