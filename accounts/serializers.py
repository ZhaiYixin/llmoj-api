from rest_framework.serializers import ModelSerializer
from .models import CustomUser

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
