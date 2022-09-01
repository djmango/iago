import dataclasses
import datetime
import hashlib
import json
import logging
import threading
import time
import unicodedata
from collections.abc import Collection
from uuid import UUID

from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.db import models
from iago.settings import ALLOWED_FILES, LOGGING_LEVEL_MODULE

from v0 import ai

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


def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.

    Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

    Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.

    Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    https://stackoverflow.com/questions/19989481/how-to-determine-if-a-string-is-a-valid-v4-uuid
    """

    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.next_call = time.time()
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self.next_call += self.interval
            self._timer = threading.Timer(self.next_call - time.time(), self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


def allowedFile(filename):
    """ Checks if the file is allowed to be processed """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILES


def truncateTextNTokens(text: str, n: int = ai.SUMMARIZER_CONFIG['MAX_TOKENS']):
    """ Truncates text to n tokens

    Args:
        text (str): Text to truncate
        n (int): Number of tokens to truncate to

    Returns:
        str: Truncated text
        int: Number of tokens
    """
    while len(ai.tokenizer(text)['input_ids']) > n:
        ten_percent = len(text) // 10
        text = text[:-ten_percent]
    return text, len(ai.tokenizer(text)['input_ids'])


def mediumReadtime(text: str) -> int:
    """ Calculates the readtime of a text in seconds """
    return round(words_in(text) / 265 * 60)

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


def generate_cache_key(*args, **kwargs):
    return str(get_hash((args, kwargs)).hex())


def search_fuzzy_cache(model: models.Model, name: str, k=1, use_cached=True, search_field='pk', queryset=None):
    """ Gets closest queryset object to the given name

    Args:
        model (django.db.models.Model): Model type to search
        name (str): Name to find closest match to
        k (int): Max number of results to return
        use_cashed (bool, optional): Allow pulling a search result from cache, defaults to True
        search_field (str, optional): Fieldname to perform the search on for, defaults to 'pk'
        queryset (django.db.models.QuerySet, optional): QuerySet to search within, use for prefiltering, defaults to None (model.objects.all())
    Returns:
        QuerySet: K closest matched instances, from cache if available
        List: Pks of closest matched instances ordered by similarity
    """

    assert isinstance(queryset, models.query.QuerySet) or queryset is None, 'queryset must be a QuerySet or None'
    if queryset is None:
        logger.debug(f'No queryset provided, using {model.__name__}.objects.all()')
        queryset = model.objects.all()
    assert isinstance(queryset.model, type(model)), 'queryset must be of the same model type as model param'

    # check if available in cache first
    cache_key = generate_cache_key(str(model._meta).lower(), name, k, search_field, str(queryset.query), version=8)  # change version every time you modify this line
    cached_results = cache.get(cache_key)
    if use_cached and cached_results and type(cached_results) == tuple:  # if so do a simple pk lookup
        results, results_pk = cached_results  # unpack tuple
    else:  # if not in cache, find the closest match using trigram and store the result in cache
        # So essentially, querysets are lazy loading
        # so we have to force the execution now
        # and then cache a queryset thats just filtering for the resulting pks
        # otherwise we cache a trigram similarity query which is much slower to execute
        results_pk = list(queryset.annotate(similarity=TrigramSimilarity(search_field, name)).order_by('-similarity')[:k].values_list('pk', flat=True))
        results = model.objects.filter(pk__in=results_pk) # We can't use our prefiltered queryset here because it's sliced and we can't filter a sliced queryset
        cache.set(cache_key, (results, results_pk), timeout=60*60*24*2)  # 2 day timeout

    return results, results_pk
