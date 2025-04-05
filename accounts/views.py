from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError

from .serializers import RegisterSerializer, UserSerializer


# 注册视图
class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'message': '注册成功',
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 登录视图
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            raise ValidationError('账号和密码是必填项')

        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'message': '登录成功',
                'token': token.key
            }, status=status.HTTP_200_OK)
        return Response({'error': '账号或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)

# 登出视图
@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    if request.user.is_authenticated:
        request.user.auth_token.delete()
        return Response({'message': '登出成功'}, status=status.HTTP_200_OK)
    return Response({'error': '用户未登录'}, status=status.HTTP_400_BAD_REQUEST)

# 用户信息视图
class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
