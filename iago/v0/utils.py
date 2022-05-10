import json
import logging
import time
import unicodedata

from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.db import models
from iago.settings import LOGGING_LEVEL_MODULE

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)


def clean_str(s: str):
    """ custom string cleaner, returns normalized unicode with spaces trimmed

        Args:
            string(str)

        Returns:
            string(str): normalized unicode string with spaces trimmed
    """
    return unicodedata.normalize('NFC', str(s.strip()))


def words_in(s: str):
    """ counts space seperated words in string

    Args:
        s (str): string to count words of

    Returns:
        int: number of words in s split my spaces
    """
    return len(s.split(' '))


def is_valid_json(s: str):
    """ returns false if s is not a valid JSON string, else returns s as a json object

    Args:
        s (str): string to check

    Returns:
        False if s is not a valid JSON string, else returns s as a json object
    """
    try:
        json.loads(s)
        return True
    except ValueError:
        return False


def search_fuzzy_cache(model: models.Model, name: str, no_cache=False):
    """ Gets closest queryset object to the given name

    Args:
        model (django.db.models.Model): Model type to search
        name (str): Name to find closest match to
        no_cache (bool, optional): Disallow pulling a search result from cache, defaults to False

    Returns:
        model instance: Closest matched instance, from cache if available
    """

    # check if available in cache first
    start = time.perf_counter()
    name_cachesafe = f"{str(model._meta).lower()}_trigram_{name.lower().replace(' ', '_')}"
    cached_object = cache.get(name_cachesafe)
    if cached_object and not no_cache:  # if so do a simple pk lookup
        object = model.objects.get(name=cached_object)
        logger.debug(f'Get cache for {name} took {time.perf_counter()-start:.3f}s')
    else:  # if not in cache, find the closest match using trigram and store the result in cache
        object = model.objects.annotate(similarity=TrigramSimilarity('name', name)).filter(similarity__gt=0.7).order_by('-similarity').first()
        if object is not None:
            cache.set(name_cachesafe, object.name, timeout=60*60*24*7)  # 7 day timeout
        logger.debug(f'Trigram search and set cache for {name} took {time.perf_counter()-start:.3f}s')

    return object
