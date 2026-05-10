from django.db import transaction
from rest_framework import serializers
from ..models import User, UserRole, JobPosition, EmployeeProfile
from datetime import date

from ...parking.models import ParkingLot


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
        fields = ['id', 'username', 'full_name', 'avatar', 'email', 'address', 'birth', 'age', 'password', 'user_role']
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
class StaffSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    birth = serializers.IntegerField(source='user.birth', read_only=True)
    address = serializers.CharField(source='user.address', read_only=True)
    user_role = serializers.CharField(source='user.user_role', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    base_salary = serializers.DecimalField(source='job_position.base_salary', read_only=True, max_digits=12, decimal_places=2)
    title = serializers.CharField(source='job_position.title', read_only=True)
    age = serializers.SerializerMethodField(read_only=True)


    class Meta:
        model = EmployeeProfile
        fields = [
            'id', 'user_id', 'username', 'full_name', 'email', 'avatar', 'age',
            'birth', 'address', 'user_role', 'is_active', 'title', 'base_salary'
        ]

    def get_age(self, obj):
        if not obj.user.birth:
            return None
        try:
            today = date.today()
            age = today.year - obj.user.birth
            return max(0, age)
        except (ValueError, TypeError):
            return None

    def create(self, validated_data):
        parking_lot = validated_data.pop("parking_lot")
        job_position = validated_data.pop("job_position")

        validated_data['user_role'] = UserRole.STAFF

        with transaction.atomic():
            user = User.objects.create_user(**validated_data)
            EmployeeProfile.objects.create(
                user=user,
                parking_lot=parking_lot,
                job_position=job_position)
        return user
