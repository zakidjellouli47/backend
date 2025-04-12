from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.contrib.auth import authenticate
from .serializers import UserSerializer, LoginSerializer
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(
        username=serializer.validated_data['email'],  # Using email as username
        password=serializer.validated_data['password']
    )
    
    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user_id': user.id,
        'email': user.email
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_auth(request):
    return Response({
        'message': 'Authenticated',
        'user_id': request.user.id,
        'email': request.user.email,
        'is_candidate': request.user.is_candidate,
        'is_elector': request.user.is_elector
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    # Delete the token to log out
    request.auth.delete()
    return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)

@api_view(['GET'])
def home(request):
    return Response({
        "message": "Welcome to the API",
        "endpoints": {
            "register": "/register/",
            "login": "/login/",
            "verify-auth": "/verify-auth/",
            "logout": "/logout/"
        }
    }, status=200)