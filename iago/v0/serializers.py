from rest_framework import serializers

class fileUploadSerializer(serializers.Serializer):
    files = serializers.FileField(max_length=100, allow_empty_file=False)
