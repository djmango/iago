import logging
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from v0.ai import embedding_model

logger = logging.getLogger(__name__)


class StringEmbedding(models.Model):
    """ Abstract class for string-embedding pairs """
    name = models.CharField(max_length=255, primary_key=True, editable=False)
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768)

    def create(self, name: str):
        """ Set name and generate embedding """
        self.name = name.lower()
        self.embedding_all_mpnet_base_v2 = list(embedding_model.model.encode(name))
        return self

    def __str__(self):
        return str(self.name)

    class Meta:
        abstract = True


class Topic(StringEmbedding):
    """ Topic object, with embedding field """
    pass


class Job(StringEmbedding):
    """ Job object, a job title and assosiated embedding field """
    pass


class Skill(StringEmbedding):
    cluster = models.ForeignKey('SkillCluster', on_delete=models.SET_NULL, blank=True, null=True)



# todo here is make a script or a method to get all the image collections and assosiate them with skills or images or something
class Image(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=800, unique=True, editable=False)
    domain = models.CharField(max_length=30, editable=False)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    url_alive = models.BooleanField(default=True)

    class providers(models.TextChoices):
        UNSPLASH = 'unsplash', 'Unsplash'
        PEXELS = 'pexels', 'Pexels'
        SHUTTERSTOCK = 'shutterstock', 'Shutterstock'
        GCC_DATASET = 'gcc_dataset', 'Google Conceptual Captions Dataset'

    provider = models.CharField(max_length=30, choices=providers.choices)

    def __str__(self):
        # if self.name:
        #     s = self.name
        # elif self.description:
        #     s = self.description
        # else:
        #     s = self.url
        # return str(s)
        return str(self.url)


class Content(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=800, unique=True)
    author = models.TextField()
    title = models.TextField()
    subtitle = models.TextField(blank=True, null=True)
    thumbnail = models.URLField(blank=True, null=True)
    thumbnail_alternative = models.ForeignKey(Image, on_delete=models.SET_NULL, blank=True, null=True)
    thumbnail_alternative_url = models.URLField(blank=True, null=True)  # this is just to make it easier for the main api, since it only has access to a non-relational mirror of the database
    content = models.TextField()
    # https://pypi.org/project/readtime/
    content_read_seconds = models.IntegerField()  # seconds = num_words / 265 * 60 + img_weight * num_images
    provider = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
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
