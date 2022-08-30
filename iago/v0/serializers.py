# https://www.django-rest-framework.org/api-guide/serializers/
from rest_framework import serializers
from enum import Enum
from django.db import models
from v0.models import Content

# TODO: implement this https://github.com/AltSchool/dynamic-rest

# * Validators
class Operator(Enum):
    GREATER_THAN = '>'
    LESS_THAN = '<'
    GREATER_THAN_OR_EQUAL_TO = '>='
    LESS_THAN_OR_EQUAL_TO = '<='
    EQUAL_TO = '=='

class CompareValues:
    """ Compares values to the initial base value and returns a serializer.ValidationError if the comparison fails. """
    def __init__(self, operator, base_value: int):
        assert operator in Operator, f'{self.operator} is not a valid operator: {Operator.__members__}'
        assert isinstance(base_value, (int, float)), 'base_value must be an integer or float'

        self.operator = operator
        self.base_value = base_value

    def __call__(self, value):
        assert isinstance(value, (int, float)), 'value must be an integer or float'
        if self.operator == Operator.GREATER_THAN:
            if not value > self.base_value:
                raise serializers.ValidationError(f'Value ({value}) must be greater than {self.base_value}')
        elif self.operator == Operator.LESS_THAN:
            if not value < self.base_value:
                raise serializers.ValidationError(f'Value ({value}) must be less than {self.base_value}')
        elif self.operator == Operator.GREATER_THAN_OR_EQUAL_TO:
            if not value >= self.base_value:
                raise serializers.ValidationError(f'Value ({value}) must be greater than or equal to {self.base_value}')
        elif self.operator == Operator.LESS_THAN_OR_EQUAL_TO:
            if value <= self.base_value:
                raise serializers.ValidationError(f'Value ({value}) must be less than or equal to {self.base_value}')

        return value

class ItemsInSet:
    """ Validate that every value in a given list is within a base set. """
    def __init__(self, base_set: set | list):
        assert isinstance(base_set, (set, list)), 'base_set must be a set'
        self.base_set = base_set

    def __call__(self, value: list):
        assert isinstance(value, list), 'value must be a list'
        for item in value:
            if item not in self.base_set:
                raise serializers.ValidationError(f'{item} is not in the base set: {self.base_set}')
        return value

class FieldsInModel:
    """ Checks if a field is in the model. """
    def __init__(self, model: models.Model | None = None):
        self.model = model
        if self.model:
            self.model_fields = ['pk'] + [x.name for x in self.model._meta.get_fields()]

    def __call__(self, requested_fields: list[str], model: models.Model | None = None):
        if model is None: # Allow passing in a model to check against at runtime, otherwise use default model
            assert self.model is not None, 'Model must be passed in or set as a default upon initialization'
        else:
            self.model = model
            self.model_fields = ['pk'] + [x.name for x in self.model._meta.get_fields()]

        # validate requested return fields
        if any(x not in self.model_fields for x in requested_fields):
            raise serializers.ValidationError(f'{self.model.__name__} does not have the following fields: {[x for x in requested_fields if x not in self.model_fields]} | Available fields: {self.model_fields}')

        if not 'pk' in requested_fields: # pk is always returned, might move this behavior to views later
            requested_fields.append('pk')

        return requested_fields

# * Reusable fields
# temperature = serializers.IntegerField(validators=[CompareValues(Operator.GREATER_THAN_OR_EQUAL_TO, 0), CompareValues(Operator.LESS_THAN_OR_EQUAL_TO, 100)])

# * Serializers
class fileUploadSerializer(serializers.Serializer):
    files = serializers.FileField(max_length=100, allow_empty_file=False)

class ContentRecommendationBySkillSerializer(serializers.Serializer):
    skills = serializers.ListField(child=serializers.CharField())
    fields = serializers.ListField(child=serializers.CharField(), validators=[FieldsInModel(Content)], default=['pk'])
    k = serializers.IntegerField(validators=[CompareValues(Operator.GREATER_THAN, 0)], default=10)
    page = serializers.IntegerField(validators=[CompareValues(Operator.GREATER_THAN_OR_EQUAL_TO, 0)], default=0)
    provider = serializers.ListField(child=serializers.CharField(), validators=[ItemsInSet(Content.providers.names)], required=False)
    content_type = serializers.ListField(child=serializers.CharField(), validators=[ItemsInSet(Content.content_types.names)], required=False)
    individual_skill_recommendations = serializers.BooleanField(default=True)
