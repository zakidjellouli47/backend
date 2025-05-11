from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Election, Candidate, Vote
from blockchain import EthereumHandler, HyperledgerHandler, IPFSHandler
import json

eth = EthereumHandler()
hlf = HyperledgerHandler()
ipfs = IPFSHandler()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_election(request):
    if not request.user.is_elector:
        return Response({'error': 'Only electors can create elections'}, 
                      status=status.HTTP_403_FORBIDDEN)

    required_fields = ['title', 'description', 'start_time', 'end_time', 'blockchain']
    if not all(field in request.data for field in required_fields):
        return Response({'error': 'Missing required fields'}, 
                      status=status.HTTP_400_BAD_REQUEST)

    try:
        # IPFS Metadata
        ipfs_data = {
            'description': request.data['description'],
            'rules': request.data.get('rules', ''),
            'options': request.data.get('options', {})
        }
        ipfs_hash = ipfs.add_json(ipfs_data)
        
        # Blockchain Operation
        if request.data['blockchain'] == 'ETH':
            election_id = eth.create_election(
                request.data['title'],
                request.data['description'],
                int(request.data['start_time']),
                int(request.data['end_time'])
            )
        else:
            election_id = hlf.create_election(
                request.data['title'],
                request.data['description'],
                int(request.data['start_time']),
                int(request.data['end_time'])
            )

        # Database Record
        election = Election.objects.create(
            title=request.data['title'],
            description=request.data['description'],
            start_time=request.data['start_time'],
            end_time=request.data['end_time'],
            blockchain=request.data['blockchain'],
            election_id=election_id,
            ipfs_hash=ipfs_hash,
            created_by=request.user
        )

        return Response({
            'id': election.id,
            'election_id': election_id,
            'ipfs_hash': ipfs_hash
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def election_results(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    
    if election.is_active:
        return Response({'error': 'Results not available until election ends'}, 
                      status=status.HTTP_400_BAD_REQUEST)

    candidates = election.candidates.order_by('-votes_received')
    results = {
        'election': {
            'title': election.title,
            'total_votes': sum(c.votes_received for c in candidates)
        },
        'candidates': [
            {
                'id': c.id,
                'user': c.user.username,
                'votes': c.votes_received
            } for c in candidates
        ]
    }
    
    return Response(results)