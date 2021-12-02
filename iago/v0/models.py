import logging
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from v0.ai import embedding_model

logger = logging.getLogger(__name__)


class Article(models.Model): # this is the scraped article, not our internal content representation
    title = models.TextField()
    content = models.TextField()
    url = models.URLField(max_length=800)
    tags = models.JSONField(default=list)

    def __str__(self):
        return str(self.title)

    class Meta:
        db_table = 'articles'

class CachedJSON(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    value = models.JSONField(default=dict)
    last_modified = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cachedjson'

class Content(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # status
    QUEUED = 'QUEUED'
    PROCESSING = 'PROCESSING'
    FINISHED = 'FINISHED'
    ERRORED = 'ERRORED'
    status = models.CharField(max_length=15, choices=[(QUEUED, 'Queued'), (PROCESSING, 'Processing'), (FINISHED, 'Finished'), (ERRORED, 'Errored')], default=QUEUED)

    # urls
    url_submitted = models.URLField(max_length=800)
    url_response = models.URLField(max_length=800, blank=True, null=True)

    # timestamps
    datetime_start = models.DateTimeField(default=timezone.now)
    datetime_end = models.DateTimeField(blank=True, null=True)

    # integrations
    diffbot_response = models.JSONField(default=dict) # raw response from diffbot
    
    # environment
    LIVE = 'LIVE'
    TEST = 'TEST'
    environment = models.CharField(max_length=15, choices=[(LIVE, 'live'), (TEST, 'test')], default=TEST)

    # article fields
    title = models.TextField(blank=True, null=True)
    isEnglish = models.BooleanField(blank=True, null=True)
    isArticle = models.BooleanField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list)

    # ai fields
    topic = models.TextField(blank=True, null=True)
    inferences = models.JSONField(default=dict) # key-value pair of model name and resulting inference
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768, blank=True, null=True)

    def __str__(self):
        if self.title is not None:
            return str(self.title)
        else:
            return str(self.id)

class Topic(models.Model):
    """ Topic object, with embedding field """
    name = models.CharField(max_length=50, primary_key=True, editable=False)
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768)

    def create(self, name: str):
        """ Set name and generate embedding """
        self.name = name.lower()
        self.embedding_all_mpnet_base_v2 = list(embedding_model.model.encode(name))
        return self

    def __str__(self):
        return str(self.name)
