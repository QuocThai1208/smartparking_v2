from rest_framework import serializers
from ..models import User, UserRole
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
        fields = ['username', 'full_name', 'avatar', 'email', 'address', 'birth', 'age', 'password', 'user_role']
        extra_kwargs = {
            'password': {'write_only': True},
            'user_role': {'read_only': True}
        }

    def get_age(self, obj):
        if not obj.birth:
            return None
        today = date.today()
        return today.year - obj.birth


class BaseUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    age = serializers.SerializerMethodField(read_only=True)
    user_role = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'avatar', 'email', 'birth', 'address', 'age', 'user_role', 'is_active', 'password')
        extra_kwargs = {
            'avatar': {'required': False, 'allow_null': True},
            'birth': {'required': False, 'allow_null': True},
            'address': {'required': False, 'allow_null': True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url if instance.avatar else ''
        return data

    def get_age(self, obj):
        if not obj.birth:
            return None
        try:
            today = date.today()
            age = today.year - obj.birth
            return max(0, age)
        except (ValueError, TypeError):
            return None


class UpdateEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'full_name', 'avatar', 'birth', 'address', 'user_role']
        extra_kwargs = {
            'avatar': {'required': False, 'allow_null': True},
            'birth': {'required': False, 'allow_null': True},
            'address': {'required': False, 'allow_null': True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url if instance.avatar else ''
        return data


class UpdateActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']


# Serializer để đăng ký User mới
class CustomerRegisterSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


# Serializer để đăng ký nhân viên mới
class StaffRegisterSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields

    def create(self, validated_data):
        role = self.context.get('role', UserRole.STAFF)
        validated_data['user_role'] = role
        user = User.objects.create_user(**validated_data)
        return user
