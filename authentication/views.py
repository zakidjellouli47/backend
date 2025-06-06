from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import User
from .serializers import UserRegistrationSerializer, UserLoginSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username,
            'is_candidate': user.is_candidate,
            'is_elector': user.is_elector
        }, status=status.HTTP_201_CREATED)
    
    # Fix error response format to match frontend expectations
    error_messages = []
    for field, errors in serializer.errors.items():
        for error in errors:
            error_messages.append(f"{field}: {error}")
    
    return Response({
        'error': ' '.join(error_messages)
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username,
            'is_candidate': user.is_candidate,
            'is_elector': user.is_elector,
            'wallet_address': user.wallet_address
        })
    
    # Fix error response format to match frontend expectations
    return Response({
        'error': 'Invalid email or password'
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except:
        return Response({'error': 'Error logging out'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def connect_wallet(request):
    wallet_address = request.data.get('wallet_address')
    if not wallet_address:
        return Response({'error': 'Wallet address required'}, status=status.HTTP_400_BAD_REQUEST)
    
    request.user.wallet_address = wallet_address
    request.user.save()
    
    return Response({
        'message': 'Wallet connected successfully',
        'wallet_address': wallet_address
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_auth(request):
    return Response({
        'user_id': request.user.pk,
        'email': request.user.email,
        'username': request.user.username,
        'is_candidate': request.user.is_candidate,
        'is_elector': request.user.is_elector,
        'wallet_address': request.user.wallet_address
    })