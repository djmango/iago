import dataclasses
import datetime
import hashlib
import json
import logging
import time
import unicodedata
from collections.abc import Collection

from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.db import models
from iago.settings import ALLOWED_FILES, LOGGING_LEVEL_MODULE

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


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def allowedFile(filename):
    """ Checks if the file is allowed to be processed """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILES


#  -- Deterministic Hashing --


"""
https://death.andgravity.com/stable-hashing
Generate stable hashes for Python data objects.
Contains no business logic.
The hashes should be stable across interpreter implementations and versions.
Supports dataclass instances, datetimes, and JSON-serializable objects.
Empty dataclass fields are ignored, to allow adding new fields without
the hash changing. Empty means one of: None, '', (), [], or {}.
The dataclass type is ignored: two instances of different types
will have the same hash if they have the same attribute/value pairs.
https://github.com/lemon24/reader/blob/1efcd38c78f70dcc4e0d279e0fa2a0276749111e/src/reader/_hash_utils.py
"""

# The first byte of the hash contains its version,
# to allow upgrading the implementation without changing existing hashes.
# (In practice, it's likely we'll just let the hash change and update
# the affected objects again; nevertheless, it's good to have the option.)
#
# A previous version recommended using a check_hash(thing, hash) -> bool
# function instead of direct equality checking; it was removed because
# it did not allow objects to cache the hash.

_VERSION = 0
_EXCLUDE = '_hash_exclude_'


def get_hash(thing: object) -> bytes:
    prefix = _VERSION.to_bytes(1, 'big')
    digest = hashlib.md5(_json_dumps(thing).encode('utf-8')).digest()
    return prefix + digest[:-1]


def _json_dumps(thing: object) -> str:
    return json.dumps(
        thing,
        default=_json_default,
        # force formatting-related options to known values
        ensure_ascii=False,
        sort_keys=True,
        indent=None,
        separators=(',', ':'),
    )


def _json_default(thing: object) -> any:
    try:
        return _dataclass_dict(thing)
    except TypeError:
        pass
    if isinstance(thing, datetime.datetime):
        return thing.isoformat(timespec='microseconds')
    raise TypeError(f"Object of type {type(thing).__name__} is not JSON serializable")


def _dataclass_dict(thing: object) -> dict[str, any]:
    # we could have used dataclasses.asdict()
    # with a dict_factory that drops empty values,
    # but asdict() is recursive and we need to intercept and check
    # the _hash_exclude_ of nested dataclasses;
    # this way, json.dumps() does the recursion instead of asdict()

    # raises TypeError for non-dataclasses
    fields = dataclasses.fields(thing)
    # ... but doesn't for dataclass *types*
    if isinstance(thing, type):
        raise TypeError("got type, expected instance")

    exclude = getattr(thing, _EXCLUDE, ())

    rv = {}
    for field in fields:
        if field.name in exclude:
            continue

        value = getattr(thing, field.name)
        if value is None or not value and isinstance(value, Collection):
            continue

        rv[field.name] = value

    return rv


def search_fuzzy_cache(model: models.Model, name: str, k=1, similarity_minimum=0.7, use_cached=True):
    """ Gets closest queryset object to the given name

    Args:
        model (django.db.models.Model): Model type to search
        name (str): Name to find closest match to
        k (int): Max number of results to return
        similarity_minimum (float): Minimum similarity (max 1)
        use_cashed (bool, optional): Allow pulling a search result from cache, defaults to True

    Returns:
        QuerySet: K Closest matched instances, from cache if available
        List: Pks of closest matched instances ordered by similarity
    """

    # check if available in cache first
    start = time.perf_counter()
    cache_key = f"{str(model._meta).lower()}_{get_hash(name).hex()}_k{k}"
    cached_results = cache.get(cache_key)
    if use_cached and cached_results and type(cached_results) == tuple:  # if so do a simple pk lookup
        results, results_pk = cached_results # unpack tuple
    else:  # if not in cache, find the closest match using trigram and store the result in cache
        # So essentially, querysets are lazy loading
        # so we have to force the execution now
        # and then cache a queryset thats just filtering for the resulting pks
        # otherwise we cache a trigram similarity query which is much slower to execute
        results_pk = list(model.objects.annotate(similarity=TrigramSimilarity('name', name)).filter(similarity__gte=similarity_minimum).order_by('-similarity')[:k].values_list('pk', flat=True))
        results = model.objects.filter(pk__in=results_pk)
        cache.set(cache_key, (results, results_pk), timeout=60*60*24*2)  # 2 day timeout
        # logger.debug(f'Trigram search and set cache for {name} took {time.perf_counter()-start:.3f}s')

    return results, results_pk
