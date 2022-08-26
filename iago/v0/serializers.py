# https://www.django-rest-framework.org/api-guide/serializers/
from rest_framework import serializers
from enum import Enum

# * Validators
class Operator(Enum):
    GREATER_THAN = '>'
    LESS_THAN = '<'
    GREATER_THAN_OR_EQUAL_TO = '>='
    LESS_THAN_OR_EQUAL_TO = '<='
    EQUAL_TO = '=='

class CompareValues:
    def __init__(self, operator, base_value: int):
        assert operator in Operator, f'{self.operator} is not a valid operator: {Operator.__members__}'
        assert isinstance(base_value, (int, float)), 'base_value must be an integer or float'

        self.operator = operator
        self.base_value = base_value

    def __call__(self, value):
        assert isinstance(value, (int, float)), 'value must be an integer or float'
        if self.operator == Operator.GREATER_THAN:
            if not value > self.base_value:
                raise serializers.ValidationError(f'{value} must be greater than {self.base_value}')
        elif self.operator == Operator.LESS_THAN:
            if not value < self.base_value:
                raise serializers.ValidationError(f'{value} must be less than {self.base_value}')
        elif self.operator == Operator.GREATER_THAN_OR_EQUAL_TO:
            if not value >= self.base_value:
                raise serializers.ValidationError(f'{value} must be greater than or equal to {self.base_value}')
        elif self.operator == Operator.LESS_THAN_OR_EQUAL_TO:
            if value <= self.base_value:
                raise serializers.ValidationError(f'{value} must be less than or equal to {self.base_value}')

        return value

# * Reusable fields
k = serializers.IntegerField(validators=[CompareValues(Operator.GREATER_THAN, 0)])

class fileUploadSerializer(serializers.Serializer):
    files = serializers.FileField(max_length=100, allow_empty_file=False)
