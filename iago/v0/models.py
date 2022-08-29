import logging
import uuid

import numpy as np
from django.contrib.postgres.fields import ArrayField
from django.db import models
from iago.settings import LOGGING_LEVEL_MODULE, MODEL_VECTOR_SIZE

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)

# -- StringEmbedding and children --


class StringEmbedding(models.Model):
    """ Abstract class for string-embedding pairs """
    name = models.CharField(max_length=255, primary_key=True, editable=False)
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=MODEL_VECTOR_SIZE)

    def create(self, name: str, embedding: list | np.ndarray | None = None):
        """ Set name and generate embedding """
        self.name = name
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


class Topic(StringEmbedding):
    """ Topic object, topic name and assosiated embedding field """
    pass


class Job(StringEmbedding):
    """ Job object, a job title and assosiated embedding field """
    pass

class MindtoolsSkillGroup(StringEmbedding):
    """ Mindtool skill area object, a skill name and assosiated embedding field """
    pass

class MindtoolsSkillSubgroup(StringEmbedding):
    """ Mindtool skill sub-area object, a skill name and assosiated embedding field """
    group = models.ForeignKey(MindtoolsSkillGroup, on_delete=models.CASCADE)

class Skill(StringEmbedding):
    """ Skill object, a skill name and assosiated embedding field """
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
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=MODEL_VECTOR_SIZE, null=True, blank=True)

    def __str__(self):
        return str(self.photo_url)

    class Meta:
        db_table = 'unsplash_photos'


# -- The core content --

class Content(models.Model):
    """ Model class for all content types """
    class providers(models.TextChoices):
        medium = 'medium'
        hbr = 'hbr'
        vodafone = 'vodafone'

    class document_types(models.TextChoices):
        article = 'article'
        video = 'video'
        pdf = 'pdf'
        invalid_file = 'invalid_file'

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=800, unique=True)
    title = models.TextField()

    author = models.TextField(blank=True, null=True)
    subtitle = models.TextField(blank=True, null=True)

    thumbnail = models.URLField(default='https://images.unsplash.com/photo-1499988921418-b7df40ff03f9') # default is just a desert picture i like :D - plus it kinda makes sense, deserts are representative of absense, so in the absense of a thumbnail, we have a desert picture. in another life im a poet or something fun like that.
    thumbnail_original = models.URLField(blank=True, null=True)
    thumbnail_alternative = models.ForeignKey(UnsplashPhoto, on_delete=models.SET_NULL, blank=True, null=True)
    
    content = models.TextField(blank=True, null=True)
    content_read_seconds = models.IntegerField(blank=True, null=True)  # https://pypi.org/project/readtime/ seconds = num_words / 265 * 60 + img_weight * num_images
    markdown = models.TextField(blank=True, null=True)
    popularity = models.JSONField(default=dict)
    summary = models.JSONField(default=dict)
    provider = models.CharField(max_length=25, choices=providers.choices, default=providers.medium)
    type = models.CharField(max_length=25, choices=document_types.choices, default=document_types.article)
    
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    published_on = models.DateTimeField(blank=True, null=True)
    
    tags = models.JSONField(default=list)
    skills = models.ManyToManyField(Skill)
    mindtools_skill_group = models.ForeignKey(MindtoolsSkillGroup, on_delete=models.SET_NULL, blank=True, null=True)
    mindtools_skill_subgroup = models.ForeignKey(MindtoolsSkillSubgroup, on_delete=models.SET_NULL, blank=True, null=True)
    
    deleted = models.BooleanField(default=False)
    last_response = models.JSONField(default=dict)
    file = models.FileField(upload_to='content/', blank=True, null=True)

    # embeddings
    embedding_all_mpnet_base_v2 = ArrayField(models.FloatField(), size=MODEL_VECTOR_SIZE, blank=True, null=True) # TODO: make this non nullable

    def __str__(self):
        return str(self.title)

# human-readable string to model class
HUMAN_TO_MODEL = {
    'content': Content,
    'Job': Job,
    'skill': Skill,
    'topic': Topic,
    'unsplash': UnsplashPhoto,
    'mindtools_group': MindtoolsSkillGroup,
    'mindtools_subgroup': MindtoolsSkillSubgroup,
}