from rest_framework import serializers

from v0.models import Content

class ContentSerializerWebhook(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ['id', 'url_submitted', 'url_response', 'datetime_start', 'datetime_end', 'title', 'isEnglish', 'isArticle', 'text']
