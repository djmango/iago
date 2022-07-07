import logging
import uuid

import numpy as np
from django.contrib.postgres.fields import ArrayField
from django.db import models
from iago.settings import LOGGING_LEVEL_MODULE

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)

# -- StringEmbedding and children --


class StringEmbedding(models.Model):
    """ Abstract class for string-embedding pairs """
    name = models.CharField(max_length=255, primary_key=True, editable=False)
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768)

    def create(self, name: str, embedding: list | np.ndarray | None = None):
        """ Set name and generate embedding """
        self.name = name.lower()
        self.embedding_all_mpnet_base_v2 = list(embedding)
        return self

    def __str__(self):
        return str(self.name)

    class Meta:
        abstract = True


class GenericStringEmbedding(StringEmbedding):
    """ Uncategorized generic string and embedding pair - used primarily as a persistent cache of embeddings """
    id = models.BigAutoField(primary_key=True)
    name = models.TextField(editable=False)
    pass


class Topic(StringEmbedding):
    """ Topic object, with embedding field """
    pass


class Job(StringEmbedding):
    """ Job object, a job title and assosiated embedding field """
    pass


class Skill(StringEmbedding):
    cluster = models.ForeignKey('SkillCluster', on_delete=models.SET_NULL, blank=True, null=True)


class SkillCluster(models.Model):
    id = models.BigAutoField(primary_key=True)
    k_top = models.OneToOneField(Skill, on_delete=models.PROTECT)

    def __str__(self):
        if self.k_top is not None:
            return str(self.k_top.name)
        else:
            return str(self.id)

# -- Unsplash Data --
# a NOTE for all these, for some reason the empty text fields got set to '' instead of null, so beware


class UnsplashCollection(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=11)
    collection_id = models.CharField(max_length=11)
    collection_title = models.TextField(blank=True, null=True)
    photo_collected_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'unsplash_collections'
        unique_together = (('photo_id', 'collection_id'),)


class UnsplashColor(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=11)
    hex = models.CharField(max_length=6)
    red = models.IntegerField(blank=True, null=True)
    green = models.IntegerField(blank=True, null=True)
    blue = models.IntegerField(blank=True, null=True)
    keyword = models.CharField(max_length=255, blank=True, null=True)
    ai_coverage = models.FloatField(blank=True, null=True)
    ai_score = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'unsplash_colors'
        unique_together = (('photo_id', 'hex'),)


class UnsplashConversion(models.Model):
    converted_at = models.DateTimeField(blank=True, null=True)
    conversion_type = models.CharField(max_length=255, blank=True, null=True)
    keyword = models.TextField(blank=True, null=True)
    photo_id = models.CharField(max_length=11, blank=True, null=True)
    anonymous_user_id = models.CharField(max_length=255, blank=True, null=True)
    conversion_country = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        db_table = 'unsplash_conversions'


class UnsplashKeyword(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=11)
    keyword = models.TextField()
    ai_service_1_confidence = models.FloatField(blank=True, null=True)
    ai_service_2_confidence = models.FloatField(blank=True, null=True)
    suggested_by_user = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'unsplash_keywords'
        unique_together = (('photo_id', 'keyword'),)


class UnsplashPhoto(models.Model):
    # imported fields
    photo_id = models.CharField(primary_key=True, max_length=11)
    photo_url = models.CharField(max_length=255, blank=True, null=True)
    photo_image_url = models.CharField(max_length=255, blank=True, null=True)
    photo_submitted_at = models.DateTimeField(blank=True, null=True)
    photo_featured = models.BooleanField(blank=True, null=True)
    photo_width = models.IntegerField(blank=True, null=True)
    photo_height = models.IntegerField(blank=True, null=True)
    photo_aspect_ratio = models.FloatField(blank=True, null=True)
    photo_description = models.TextField(blank=True, null=True)
    photographer_username = models.CharField(max_length=255, blank=True, null=True)
    photographer_first_name = models.CharField(max_length=255, blank=True, null=True)
    photographer_last_name = models.CharField(max_length=255, blank=True, null=True)
    exif_camera_make = models.CharField(max_length=255, blank=True, null=True)
    exif_camera_model = models.CharField(max_length=255, blank=True, null=True)
    exif_iso = models.IntegerField(blank=True, null=True)
    exif_aperture_value = models.CharField(max_length=255, blank=True, null=True)
    exif_focal_length = models.CharField(max_length=255, blank=True, null=True)
    exif_exposure_time = models.CharField(max_length=255, blank=True, null=True)
    photo_location_name = models.CharField(max_length=255, blank=True, null=True)
    photo_location_latitude = models.FloatField(blank=True, null=True)
    photo_location_longitude = models.FloatField(blank=True, null=True)
    photo_location_country = models.CharField(max_length=255, blank=True, null=True)
    photo_location_city = models.CharField(max_length=255, blank=True, null=True)
    stats_views = models.IntegerField(blank=True, null=True)
    stats_downloads = models.IntegerField(blank=True, null=True)
    ai_description = models.CharField(max_length=255, blank=True, null=True)
    ai_primary_landmark_name = models.CharField(max_length=255, blank=True, null=True)
    ai_primary_landmark_latitude = models.FloatField(blank=True, null=True)
    ai_primary_landmark_longitude = models.FloatField(blank=True, null=True)
    ai_primary_landmark_confidence = models.CharField(max_length=255, blank=True, null=True)
    blur_hash = models.CharField(max_length=255, blank=True, null=True)
    # new fields
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768, null=True, blank=True)

    class Meta:
        db_table = 'unsplash_photos'


# -- The core content --

class Content(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=800, unique=True)
    author = models.TextField()
    title = models.TextField()
    subtitle = models.TextField(blank=True, null=True)
    thumbnail = models.URLField(blank=True, null=True)
    thumbnail_alternative = models.ForeignKey(UnsplashPhoto, on_delete=models.SET_NULL, blank=True, null=True)
    thumbnail_alternative_url = models.URLField(blank=True, null=True)  # this is just to make it easier for the main api, since it only has access to a non-relational mirror of the database
    content = models.TextField(blank=True, null=True)
    # https://pypi.org/project/readtime/
    content_read_seconds = models.IntegerField(blank=True, null=True)  # seconds = num_words / 265 * 60 + img_weight * num_images
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    tags = models.JSONField(default=list)
    skills = models.ManyToManyField(Skill)
    popularity = models.JSONField(default=dict)
    deleted = models.BooleanField(default=False)
    markdown = models.TextField(blank=True, null=True)
    last_response = models.JSONField(default=dict)
    summary = models.JSONField(default=dict)
    file = models.FileField(upload_to='content/', blank=True, null=True)

    class providers(models.TextChoices):
        medium = 'medium'
        hbr = 'hbr'
        vodafone = 'vodafone'

    provider = models.CharField(max_length=25, choices=providers.choices, default=providers.medium)

    class types(models.TextChoices):
        article = 'article'
        video = 'video'
        pdf = 'pdf'
        invalid_file = 'invalid_file'

    type = models.CharField(max_length=25, choices=types.choices, default=types.article)

    # embeddings
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=768, blank=True, null=True)

    def __str__(self):
        return str(self.title)
