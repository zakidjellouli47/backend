from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
import hashlib
from datetime import datetime

from .models import User, Election, Candidate, Vote
from .serializers import UserSerializer, LoginSerializer, ElectionSerializer, CandidateSerializer, VoteSerializer
from blockchain.ethereum_handler import EthereumHandler
from blockchain.hyperledger_handler import HyperledgerHandler
from blockchain.ipfs_handler import IPFSHandler

eth = EthereumHandler()
hlf = HyperledgerHandler()
ipfs = IPFSHandler()

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
            'email': user.email,
            'is_candidate': user.is_candidate,
            'is_elector': user.is_elector
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(
        username=serializer.validated_data['email'],
        password=serializer.validated_data['password']
    )
    
    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user_id': user.id,
        'email': user.email,
        'is_candidate': user.is_candidate,
        'is_elector': user.is_elector,
        'wallet_address': user.wallet_address
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_election(request):
    if not request.user.is_elector:
        return Response({'error': 'Only electors can create elections'}, status=status.HTTP_403_FORBIDDEN)

    serializer = ElectionSerializer(data=request.data)
    if serializer.is_valid():
        ipfs_hash = ipfs.add_json({
            'description': serializer.validated_data['description'],
            'rules': request.data.get('rules', '')
        })
        
        blockchain = serializer.validated_data['blockchain']
        if blockchain == 'ETH':
            election_id = eth.create_election(
                serializer.validated_data['title'],
                serializer.validated_data['description'],
                serializer.validated_data['start_time'],
                serializer.validated_data['end_time']
            )
        else:
            election_id = hlf.invoke_chaincode(
                'CreateElection',
                [
                    serializer.validated_data['title'],
                    serializer.validated_data['description'],
                    str(int(serializer.validated_data['start_time'].timestamp())),
                    str(int(serializer.validated_data['end_time'].timestamp()))
                ]
            )
        
        election = serializer.save(
            created_by=request.user,
            ipfs_hash=ipfs_hash,
            eth_election_id=election_id if blockchain == 'ETH' else None,
            hlf_election_id=election_id if blockchain == 'HLF' else None
        )
        
        return Response(ElectionSerializer(election).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_candidate(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    
    if not request.user.is_candidate:
        return Response({'error': 'Only candidates can register'}, status=status.HTTP_403_FORBIDDEN)
    
    if Candidate.objects.filter(election=election, user=request.user).exists():
        return Response({'error': 'Already registered'}, status=status.HTTP_400_BAD_REQUEST)
    
    if election.blockchain == 'ETH':
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address required'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = eth.add_candidate(
            election.eth_election_id,
            request.user.wallet_address,
            request.user.username
        )
        candidate_id = result['logs'][0]['args']['candidateId']
    else:
        result = hlf.invoke_chaincode(
            'AddCandidate',
            [election.hlf_election_id, request.user.username]
        )
        candidate_id = hashlib.sha256(request.user.username.encode()).hexdigest()
    
    candidate = Candidate.objects.create(
        election=election,
        user=request.user,
        eth_candidate_id=candidate_id if election.blockchain == 'ETH' else None,
        hlf_candidate_id=candidate_id if election.blockchain == 'HLF' else None
    )
    
    return Response(CandidateSerializer(candidate).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cast_vote(request, election_id, candidate_id):
    election = get_object_or_404(Election, pk=election_id)
    candidate = get_object_or_404(Candidate, pk=candidate_id, election=election)
    
    if not request.user.is_elector:
        return Response({'error': 'Only electors can vote'}, status=status.HTTP_403_FORBIDDEN)
    
    if Vote.objects.filter(election=election, voter=request.user).exists():
        return Response({'error': 'Already voted'}, status=status.HTTP_400_BAD_REQUEST)
    
    if election.blockchain == 'ETH':
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address required'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = eth.cast_vote(
            election.eth_election_id,
            candidate.eth_candidate_id,
            request.user.wallet_address
        )
        tx_hash = result['transactionHash'].hex()
    else:
        tx_hash = hashlib.sha256(
            f"{election.id}{candidate.id}{request.user.id}{datetime.now().timestamp()}".encode()
        ).hexdigest()
        hlf.invoke_chaincode(
            'CastVote',
            [election.hlf_election_id, candidate.hlf_candidate_id, request.user.username]
        )
    
    vote = Vote.objects.create(
        election=election,
        voter=request.user,
        candidate=candidate,
        tx_hash=tx_hash,
        blockchain=election.blockchain
    )
    candidate.votes_received += 1
    candidate.save()
    
    return Response(VoteSerializer(vote).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def election_results(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    candidates = election.candidates.order_by('-votes_received')
    return Response({
        'election': ElectionSerializer(election).data,
        'candidates': CandidateSerializer(candidates, many=True).data
    })