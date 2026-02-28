from rest_framework import serializers
from ..models import User
from datetime import date

class UserSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url if instance.avatar else ''
        return data

    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        u.save()
        return u

    class Meta:
        model = User
        fields = ['username', 'full_name', 'avatar', 'address', 'birth', 'age', 'password', 'user_role']
        extra_kwargs = {
            'password': {'write_only': True },
            'user_role': {'read_only': True }
        }

    def get_age(self, obj):
        if not obj.birth:
            return None
        today = date.today()
        return today.year - obj.birth