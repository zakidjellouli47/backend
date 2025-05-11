from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from django.utils import timezone

from .models import User, Election, Candidate, Vote
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    ElectionSerializer,
    CandidateSerializer,
    VoteSerializer
)

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
            'is_candidate': user.is_candidate,
            'is_elector': user.is_elector
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = UserLoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'is_candidate': user.is_candidate,
            'is_elector': user.is_elector,
            'wallet_address': user.wallet_address
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_election(request):
    if not request.user.is_elector:
        return Response(
            {'error': 'Only electors can create elections'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ElectionSerializer(data=request.data)
    if serializer.is_valid():
        election = serializer.save(created_by=request.user)
        return Response(
            ElectionSerializer(election).data,
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_candidate(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    
    if not request.user.is_candidate:
        return Response(
            {'error': 'Only candidates can register'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if timezone.now() > election.start_time:
        return Response(
            {'error': 'Candidate registration period has ended'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if Candidate.objects.filter(election=election, user=request.user).exists():
        return Response(
            {'error': 'Already registered as candidate for this election'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    candidate = Candidate.objects.create(
        election=election,
        user=request.user,
        bio=request.data.get('bio', '')
    )
    
    return Response(
        CandidateSerializer(candidate).data,
        status=status.HTTP_201_CREATED
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cast_vote(request, election_id, candidate_id):
    election = get_object_or_404(Election, pk=election_id)
    candidate = get_object_or_404(Candidate, pk=candidate_id, election=election)
    
    if not request.user.is_elector:
        return Response(
            {'error': 'Only electors can vote'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not election.is_active:
        return Response(
            {'error': 'Election is not currently active'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if Vote.objects.filter(election=election, voter=request.user).exists():
        return Response(
            {'error': 'Already voted in this election'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if candidate.election != election:
        return Response(
            {'error': 'Candidate does not belong to this election'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # This would be replaced with actual blockchain transaction
    tx_hash = f"mock_tx_hash_{election_id}_{candidate_id}_{request.user.id}"
    
    vote = Vote.objects.create(
        election=election,
        voter=request.user,
        candidate=candidate,
        tx_hash=tx_hash,
        blockchain=election.blockchain
    )
    
    candidate.votes_received += 1
    candidate.save()
    
    return Response(
        VoteSerializer(vote).data,
        status=status.HTTP_201_CREATED
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def election_results(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    if timezone.now() < election.end_time:
        return Response(
            {'error': 'Results are not available until election ends'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    candidates = election.candidates.order_by('-votes_received')
    return Response({
        'election': ElectionSerializer(election).data,
        'candidates': CandidateSerializer(candidates, many=True).data
    })