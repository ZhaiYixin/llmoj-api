from rest_framework.serializers import ModelSerializer
from .models import CustomUser
from django.contrib.auth import get_user_model

class RegisterSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'full_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
        )
        return user

class UserSerializer(ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['username', 'full_name']
