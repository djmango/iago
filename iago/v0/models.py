import logging
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from v0.ai import embedding_model

logger = logging.getLogger(__name__)


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


class Job(models.Model):
    name = models.CharField(max_length=255, primary_key=True, editable=False)
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768)

    def __str__(self):
        return str(self.name)


class Skill(models.Model):
    name = models.CharField(max_length=255, primary_key=True, editable=False)
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768)
    cluster = models.ForeignKey('SkillCluster', on_delete=models.SET_NULL, blank=True, null=True)

    def create(self, name: str):
        """ Set name and generate embedding """
        self.name = name.lower()
        self.embedding_all_mpnet_base_v2 = list(embedding_model.model.encode(name))
        return self

    def __str__(self):
        return str(self.name)


class Content(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=800, unique=True)
    author = models.TextField()
    title = models.TextField()
    subtitle = models.TextField(blank=True, null=True)
    thumbnail = models.URLField(blank=True, null=True)
    content = models.TextField()
    # https://pypi.org/project/readtime/
    content_read_seconds = models.IntegerField()  # seconds = num_words / 265 * 60 + img_weight * num_images
    provider = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now_add=True)
    tags = models.JSONField(default=list)
    skills = models.ManyToManyField(Skill)
    popularity = models.JSONField(default=dict)
    deleted = models.BooleanField(default=False)

    class types(models.TextChoices):
        article = 'article'
        video = 'video'
        pdf = 'pdf'

    type = models.CharField(
        max_length=10,
        choices=types.choices,
        default=types.article,
    )

    # embeddings
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768, blank=True, null=True)

    def __str__(self):
        return str(self.title)


class SkillCluster(models.Model):
    id = models.BigAutoField(primary_key=True)
    k_top = models.OneToOneField(Skill, on_delete=models.PROTECT)

    def __str__(self):
        if self.k_top is not None:
            return str(self.k_top.name)
        else:
            return str(self.id)
