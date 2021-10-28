import logging

from django.db import models

logger = logging.getLogger(__name__)


class Article(models.Model):

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
