from rest_framework import serializers

from v0.models import Content

class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = '__all__'

class ContentSerializerWebhook(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ['id', 'url_submitted', 'url_response', 'datetime_start', 'datetime_end', 'title', 'isEnglish', 'isArticle', 'text']
