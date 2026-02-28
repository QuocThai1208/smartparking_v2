from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.users.models import User


# Tùy chỉnh nội dung bên trong JWT (Payload), kế thừa class gốc của simple jwt
class TokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Thêm các "Claims" tùy chỉnh (được bảo vệ bởi Signature)
        token['role'] = user.user_role
        token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'role': self.user.user_role,
            'avatar': self.user.avatar.url if self.user.avatar else None,
        }

        return data

# Serializer để đăng ký User mới
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'full_name', 'birth', 'address' )

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
