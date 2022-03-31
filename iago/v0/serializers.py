from rest_framework import serializers

from v0.models import Topic

class TopicSerializerAll(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = '__all__'
