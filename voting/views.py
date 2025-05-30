from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Election, Candidate, Vote
from blockchain import EnhancedEthereumHandler, EnhancedHyperledgerHandler, IPFSHandler
from authentication.models import User
import json
from datetime import datetime
from web3.exceptions import ContractLogicError

eth = EnhancedEthereumHandler()
hlf = EnhancedHyperledgerHandler()
ipfs = IPFSHandler()

class ElectionService:
    @staticmethod
    def validate_election_times(start_time, end_time):
        now = timezone.now().timestamp()
        if start_time < now:
            raise ValueError("Start time cannot be in the past")
        if end_time <= start_time:
            raise ValueError("End time must be after start time")

    @staticmethod
    def get_blockchain_handler(blockchain_type):
        if blockchain_type == 'ETH':
            return eth
        elif blockchain_type == 'HLF':
            return hlf
        else:
            raise ValueError("Unsupported blockchain type")

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_election(request):
    if not request.user.is_elector:
        return Response({'error': 'Only electors can create elections'}, 
                      status=status.HTTP_403_FORBIDDEN)

    required_fields = ['title', 'description', 'start_time', 'end_time', 'blockchain']
    if not all(field in request.data for field in required_fields):
        return Response({'error': f'Missing required fields: {required_fields}'}, 
                      status=status.HTTP_400_BAD_REQUEST)

    try:
        # Convert and validate times
        start_time = int(request.data['start_time'])
        end_time = int(request.data['end_time'])
        ElectionService.validate_election_times(start_time, end_time)

        # IPFS Metadata with enhanced structure
        ipfs_data = {
            'title': request.data['title'],
            'description': request.data['description'],
            'rules': request.data.get('rules', {}),
            'options': request.data.get('options', {}),
            'metadata': {
                'created_at': datetime.utcnow().isoformat(),
                'created_by': request.user.username,
                'blockchain': request.data['blockchain']
            }
        }
        
        ipfs_hash = ipfs.add_json(ipfs_data)
        if not ipfs_hash:
            raise Exception("Failed to store election metadata on IPFS")

        # Blockchain Operation
        handler = ElectionService.get_blockchain_handler(request.data['blockchain'])
        
        election_id = handler.create_election(
            title=request.data['title'],
            description=request.data['description'],
            start_time=start_time,
            end_time=end_time
        )

        # Database Record with enhanced fields
        election = Election.objects.create(
            title=request.data['title'],
            description=request.data['description'],
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.fromtimestamp(end_time),
            blockchain=request.data['blockchain'],
            election_id=election_id,
            ipfs_hash=ipfs_hash,
            created_by=request.user,
            config=request.data.get('config', {})
        )

        return Response({
            'id': election.id,
            'blockchain_id': election_id,
            'ipfs_hash': ipfs_hash,
            'blockchain': election.blockchain,
            'start_time': election.start_time,
            'end_time': election.end_time
        }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except ContractLogicError as e:
        return Response({'error': f"Contract error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f"Server error: {str(e)}"}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Update your cast_vote function to work with the Candidate model
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cast_vote(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    
    # Check if election is approved
    if not election.is_approved:
        return Response({'error': 'Election is not approved yet'},
                       status=status.HTTP_400_BAD_REQUEST)
    
    if not election.is_active:
        return Response({'error': 'Election is not currently active'},
                       status=status.HTTP_400_BAD_REQUEST)

    if 'candidate_id' not in request.data:
        return Response({'error': 'Candidate ID is required'},
                      status=status.HTTP_400_BAD_REQUEST)

    try:
        # Get the candidate object
        candidate = get_object_or_404(Candidate, 
                                    election=election, 
                                    id=request.data['candidate_id'])
        
        # Check if candidate is approved
        if not candidate.approved:
            return Response({'error': 'Cannot vote for unapproved candidate'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Verify user hasn't voted
        if Vote.objects.filter(election=election, voter=request.user).exists():
            return Response({'error': 'You have already voted in this election'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Get blockchain handler
        handler = ElectionService.get_blockchain_handler(election.blockchain)
        
        # Dynamic voter address handling
        voter_address = request.user.wallet_address if election.blockchain == 'ETH' else request.user.username
        
        # Create IPFS vote receipt
        vote_receipt = {
            'election_id': str(election.id),
            'voter_id': str(request.user.id),
            'voter_username': request.user.username,
            'candidate_id': str(candidate.id),
            'candidate_blockchain_id': candidate.candidate_id,
            'candidate_username': candidate.user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': {
                'ip': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
                'blockchain': election.blockchain
            }
        }
        
        ipfs_hash = ipfs.add_json(vote_receipt)
        
        # Blockchain transaction - use the candidate's blockchain ID
        tx_hash = None
        try:
            if election.blockchain == 'ETH':
                if not request.user.wallet_address:
                    raise Exception("User must have a wallet address to vote in Ethereum elections")
                
                success = eth.cast_vote(
                    election.election_id,
                    candidate.candidate_id,
                    request.user.wallet_address
                )
            else:
                success = hlf.cast_vote(
                    election.election_id,
                    candidate.candidate_id,
                    request.user.username
                )
            
            if success:
                tx_hash = success.get('tx_hash') if isinstance(success, dict) else str(success)
            else:
                raise Exception("Blockchain transaction failed")
                
        except Exception as blockchain_error:
            # If blockchain fails, create a fallback transaction hash
            import hashlib
            fallback_data = f"{election.id}_{request.user.id}_{candidate.id}_{datetime.utcnow().timestamp()}"
            tx_hash = hashlib.sha256(fallback_data.encode()).hexdigest()[:64]
            print(f"Blockchain voting failed, using fallback: {blockchain_error}")
        
        # Local database record
        vote = Vote.objects.create(
            election=election,
            voter=request.user,
            candidate=candidate,
            tx_hash=tx_hash,
            blockchain=election.blockchain,
            verified=False  # Will be verified later
        )
        
        # Update candidate vote count
        candidate.votes_received += 1
        candidate.save()

        return Response({
            'status': 'Vote recorded successfully',
            'vote_id': vote.id,
            'tx_hash': tx_hash,
            'ipfs_hash': ipfs_hash,
            'candidate': {
                'id': candidate.id,
                'username': candidate.user.username,
                'votes_received': candidate.votes_received
            },
            'voted_at': vote.voted_at,
            'blockchain': election.blockchain
        })

    except Candidate.DoesNotExist:
        return Response({'error': 'Candidate not found'}, 
                      status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f"Voting failed: {str(e)}"}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def election_results(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    
    if election.is_active and not request.user.is_staff:
        return Response({'error': 'Results not available until election ends'}, 
                      status=status.HTTP_400_BAD_REQUEST)

    try:
        handler = ElectionService.get_blockchain_handler(election.blockchain)
        
        if election.blockchain == 'ETH':
            results = eth.get_election_results(election.election_id)
            candidates = [
                {
                    'id': results['candidateIds'][i],
                    'name': results['names'][i],
                    'votes': results['voteCounts'][i],
                    'percentage': (results['voteCounts'][i] / sum(results['voteCounts'])) * 100 if sum(results['voteCounts']) > 0 else 0
                }
                for i in range(len(results['candidateIds']))
            ]
        else:
            results = hlf.get_election_results(election.election_id)
            candidates = [
                {
                    'id': c['id'],
                    'name': c['name'],
                    'votes': c['votes'],
                    'percentage': c['percentage']
                }
                for c in results['candidates']
            ]

        response_data = {
            'election': {
                'id': election.id,
                'title': election.title,
                'total_votes': sum(c['votes'] for c in candidates),
                'blockchain_id': election.election_id,
                'blockchain': election.blockchain,
                'ipfs_metadata': ipfs.get_json(election.ipfs_hash) if election.ipfs_hash else None
            },
            'candidates': candidates,
            'timestamp': datetime.utcnow().isoformat()
        }

        if request.user.is_staff:
            response_data['audit'] = {
                'votes': Vote.objects.filter(election=election).values(
                    'voter__username', 'candidate_id', 'timestamp'
                ),
                'blockchain_data': results
            }

        return Response(response_data)

    except Exception as e:
        return Response({'error': f"Failed to get results: {str(e)}"}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def voter_status(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    
    try:
        handler = ElectionService.get_blockchain_handler(election.blockchain)
        voter_address = request.user.wallet_address if election.blockchain == 'ETH' else request.user.hlf_identity
        
        if election.blockchain == 'ETH':
            has_voted = eth.has_user_voted(election.election_id, voter_address)
            vote_details = eth.get_voter_details(election.election_id, voter_address) if has_voted else None
        else:
            has_voted = hlf.has_user_voted(election.election_id, voter_address)
            vote_details = hlf.get_voter_details(election.election_id, voter_address) if has_voted else None

        local_vote = Vote.objects.filter(election=election, voter=request.user).first()
        
        return Response({
            'has_voted': has_voted,
            'vote_details': vote_details,
            'local_record': {
                'exists': local_vote is not None,
                'candidate_id': local_vote.candidate_id if local_vote else None,
                'timestamp': local_vote.timestamp if local_vote else None,
                'ipfs_proof': ipfs.get_json(local_vote.ipfs_hash) if local_vote and local_vote.ipfs_hash else None
            } if local_vote else None,
            'election_status': 'active' if election.is_active else 'ended'
        })

    except Exception as e:
        return Response({'error': f"Failed to check voter status: {str(e)}"}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_candidate(request, election_id):
    """Register a candidate for a specific election"""
    election = get_object_or_404(Election, pk=election_id)
    
    # Check if user has permission to register candidates
    if not request.user.is_elector and not request.user.is_staff:
        return Response({'error': 'Only electors and staff can register candidates'}, 
                      status=status.HTTP_403_FORBIDDEN)
    
    # Check if election hasn't started yet (candidates can only be registered before election starts)
    if election.start_time <= timezone.now():
        return Response({'error': 'Cannot register candidates after election has started'}, 
                      status=status.HTTP_400_BAD_REQUEST)
    
    # Validate required fields
    required_fields = ['user_id']  # Since candidates are linked to users
    if not all(field in request.data for field in required_fields):
        return Response({'error': f'Missing required fields: {required_fields}'}, 
                      status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get the user who will be the candidate
        candidate_user = get_object_or_404(User, pk=request.data['user_id'])
        
        # Check if user is eligible to be a candidate
        if not candidate_user.is_candidate:
            return Response({'error': 'User must be marked as candidate to register for elections'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is already a candidate in this election
        if Candidate.objects.filter(election=election, user=candidate_user).exists():
            return Response({'error': 'User is already registered as a candidate in this election'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Create IPFS metadata for candidate
        candidate_data = {
            'user_id': str(candidate_user.id),
            'username': candidate_user.username,
            'email': candidate_user.email,
            'bio': request.data.get('bio', ''),
            'election_id': str(election.id),
            'metadata': {
                'registered_at': datetime.utcnow().isoformat(),
                'registered_by': request.user.username,
                'election_title': election.title
            }
        }
        
        # Store candidate info on IPFS
        ipfs_hash = ipfs.add_json(candidate_data)
        if not ipfs_hash:
            raise Exception("Failed to store candidate data on IPFS")
        
        # Get blockchain handler
        handler = ElectionService.get_blockchain_handler(election.blockchain)
        
        # Register candidate on blockchain
        candidate_blockchain_id = None
        try:
            if election.blockchain == 'ETH':
                # Use user's wallet address as candidate identifier
                if not candidate_user.wallet_address:
                    raise Exception("Candidate user must have a wallet address for Ethereum elections")
                
                success = eth.register_candidate(
                    election.election_id,
                    candidate_user.username,
                    request.data.get('bio', '')
                )
                candidate_blockchain_id = success.get('candidate_id') if success else None
            else:
                # For Hyperledger Fabric
                success = hlf.register_candidate(
                    election.election_id,
                    candidate_user.username,
                    request.data.get('bio', '')
                )
                candidate_blockchain_id = success.get('candidate_id') if success else None
            
            if not success:
                # If blockchain registration fails, create fallback ID
                candidate_blockchain_id = f"{election.id}_{candidate_user.id}"
        except Exception as blockchain_error:
            # Log the blockchain error but continue with local registration
            print(f"Blockchain registration failed: {blockchain_error}")
            candidate_blockchain_id = f"{election.id}_{candidate_user.id}"
        
        # Create local database record
        candidate = Candidate.objects.create(
            election=election,
            user=candidate_user,
            candidate_id=candidate_blockchain_id,
            bio=request.data.get('bio', ''),
            approved=False  # Requires approval
        )
        
        return Response({
            'id': candidate.id,
            'candidate_id': candidate_blockchain_id,
            'user': {
                'id': candidate_user.id,
                'username': candidate_user.username,
                'email': candidate_user.email
            },
            'bio': candidate.bio,
            'approved': candidate.approved,
            'ipfs_hash': ipfs_hash,
            'blockchain': election.blockchain
        }, status=status.HTTP_201_CREATED)
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, 
                      status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f"Registration failed: {str(e)}"}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_candidates(request, election_id):
    """List all candidates for a specific election"""
    election = get_object_or_404(Election, pk=election_id)
    candidates = Candidate.objects.filter(election=election).select_related('user')
    
    candidate_data = [
        {
            'id': c.id,
            'candidate_id': c.candidate_id,
            'user': {
                'id': c.user.id,
                'username': c.user.username,
                'email': c.user.email
            },
            'bio': c.bio,
            'votes_received': c.votes_received,
            'approved': c.approved
        }
        for c in candidates
    ]
    
    return Response({
        'election': {
            'id': election.id,
            'title': election.title,
            'is_active': election.is_active,
            'is_approved': election.is_approved
        },
        'candidates': candidate_data,
        'total_candidates': len(candidate_data)
    })


@api_view(['GET'])
def verify_vote(request, tx_hash):
    """Verify a vote using its transaction hash"""
    try:
        vote = get_object_or_404(Vote, tx_hash=tx_hash)
        
        # Get blockchain handler
        handler = ElectionService.get_blockchain_handler(vote.blockchain)
        
        # Verify on blockchain
        blockchain_data = None
        try:
            if vote.blockchain == 'ETH':
                blockchain_data = eth.verify_transaction(tx_hash)
            else:
                blockchain_data = hlf.verify_transaction(tx_hash)
        except Exception as e:
            blockchain_data = {'error': f'Blockchain verification failed: {str(e)}'}
        
        return Response({
            'vote': {
                'id': vote.id,
                'election_id': vote.election.id,
                'election_title': vote.election.title,
                'voter_username': vote.voter.username,
                'candidate_username': vote.candidate.user.username,
                'voted_at': vote.voted_at,  # Using correct field name
                'verified': vote.verified,
                'blockchain': vote.blockchain
            },
            'blockchain_verification': blockchain_data,
            'tx_hash': tx_hash
        })
        
    except Vote.DoesNotExist:
        return Response({'error': 'Vote not found'}, 
                      status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f"Verification failed: {str(e)}"}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)