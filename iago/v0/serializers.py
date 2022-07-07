from rest_framework import serializers

from v0.models import Topic

class TopicSerializerAll(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = '__all__'


class fileUploadSerializer(serializers.Serializer):
    files = serializers.FileField(max_length=100, allow_empty_file=False)
