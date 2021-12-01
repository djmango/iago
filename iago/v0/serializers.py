from rest_framework import serializers

from v0.models import Content, Topic

class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = '__all__'

class ContentSerializerWebhook(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ['id', 'url_submitted', 'url_response', 'datetime_start', 'datetime_end', 'title', 'isEnglish', 'isArticle', 'topic']

class TopicSerializerAll(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = '__all__'
