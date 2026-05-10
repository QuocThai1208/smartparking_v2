from rest_framework import serializers

from apps.users.models import JobPosition


class BaseJobPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosition
        fields = ['id', 'title', 'description', 'base_salary']