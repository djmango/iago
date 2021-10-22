import logging

from django.db import models

logger = logging.getLogger(__name__)


class Article(models.Model):

    title = models.TextField()
    content = models.TextField()
    url = models.URLField(max_length=800)

    def __str__(self):
        return str(self.title)

    class Meta:
        db_table = 'articles'
