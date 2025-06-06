from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
import logging
from datetime import datetime

# Import your blockchain handlers
from blockchain.ethereum_handler import EnhancedEthereumHandler
from blockchain.models import BlockchainTransaction

logger = logging.getLogger(__name__)

def get_blockchain_handler(blockchain_type='ETH'):
    """Get appropriate blockchain handler"""
    if blockchain_type == 'ETH':
        return EnhancedEthereumHandler()
    elif blockchain_type == 'HLF':
        # Import your hyperledger handler when ready
        # from blockchain.hyperledger_handler import HyperledgerHandler
        # return HyperledgerHandler()
        raise NotImplementedError("Hyperledger handler not implemented yet")
    else:
        raise ValueError(f"Unsupported blockchain type: {blockchain_type}")

@csrf_exempt
@require_http_methods(["GET"])
def get_elections(request):
    """Get all available elections"""
    try:
        blockchain_type = request.GET.get('blockchain', 'ETH')
        handler = get_blockchain_handler(blockchain_type)
        
        # Get elections from blockchain (you'll need to implement this in your handler)
        # For now, return a placeholder structure
        elections = []
        
        return JsonResponse({
            'success': True,
            'elections': elections,
            'blockchain': blockchain_type
        })
        
    except Exception as e:
        logger.error(f"Error getting elections: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def create_election(request):
    """Create new election on blockchain"""
    try:
        data = json.loads(request.body)
        blockchain_type = data.get('blockchain', 'ETH')
        handler = get_blockchain_handler(blockchain_type)
        
        # Extract election data
        title = data.get('title')
        description = data.get('description') 
        start_time = int(datetime.fromisoformat(data.get('start_time')).timestamp())
        end_time = int(datetime.fromisoformat(data.get('end_time')).timestamp())
        creator_address = data.get('creator_address')
        
        # Validate required fields
        if not all([title, description, start_time, end_time]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)
        
        # Create election on blockchain
        result = handler.create_election(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            creator_address=creator_address
        )
        
        # Track transaction
        BlockchainTransaction.objects.create(
            tx_hash=result['transactionHash'],
            blockchain_type=blockchain_type,
            status='confirmed',
            details={
                'type': 'create_election',
                'election_id': result['electionId'],
                'creator': creator_address
            }
        )
        
        return JsonResponse({
            'success': True,
            'election_id': result['electionId'],
            'transaction_hash': result['transactionHash'],
            'block_number': result['blockNumber']
        })
        
    except Exception as e:
        logger.error(f"Error creating election: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_election_details(request, election_id):
    """Get detailed election information"""
    try:
        blockchain_type = request.GET.get('blockchain', 'ETH')
        handler = get_blockchain_handler(blockchain_type)
        
        # Get election details from blockchain
        details = handler.get_election_details(int(election_id))
        
        return JsonResponse({
            'success': True,
            'election': details
        })
        
    except Exception as e:
        logger.error(f"Error getting election details: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def add_candidate(request, election_id):
    """Add candidate to election"""
    try:
        data = json.loads(request.body)
        blockchain_type = data.get('blockchain', 'ETH')
        handler = get_blockchain_handler(blockchain_type)
        
        candidate_address = data.get('candidate_address')
        candidate_name = data.get('candidate_name')
        caller_address = data.get('caller_address')
        
        if not all([candidate_address, candidate_name]):
            return JsonResponse({
                'success': False,
                'error': 'Missing candidate address or name'
            }, status=400)
        
        # Add candidate to blockchain
        result = handler.add_candidate(
            election_id=int(election_id),
            candidate_address=candidate_address,
            name=candidate_name,
            caller_address=caller_address
        )
        
        # Track transaction
        BlockchainTransaction.objects.create(
            tx_hash=result['transactionHash'],
            blockchain_type=blockchain_type,
            status='confirmed',
            details={
                'type': 'add_candidate',
                'election_id': election_id,
                'candidate_id': result['candidateId'],
                'candidate_address': candidate_address
            }
        )
        
        return JsonResponse({
            'success': True,
            'candidate_id': result['candidateId'],
            'transaction_hash': result['transactionHash']
        })
        
    except Exception as e:
        logger.error(f"Error adding candidate: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def cast_vote(request, election_id):
    """Cast vote on blockchain"""
    try:
        data = json.loads(request.body)
        blockchain_type = data.get('blockchain', 'ETH')
        handler = get_blockchain_handler(blockchain_type)
        
        candidate_id = data.get('candidate_id')
        voter_address = data.get('voter_address')
        
        if not all([candidate_id, voter_address]):
            return JsonResponse({
                'success': False,
                'error': 'Missing candidate_id or voter_address'
            }, status=400)
        
        # Check if user already voted
        has_voted = handler.has_user_voted(int(election_id), voter_address)
        if has_voted:
            return JsonResponse({
                'success': False,
                'error': 'User has already voted in this election'
            }, status=400)
        
        # Cast vote on blockchain
        result = handler.cast_vote(
            election_id=int(election_id),
            candidate_id=int(candidate_id),
            voter_address=voter_address
        )
        
        # Track transaction
        BlockchainTransaction.objects.create(
            tx_hash=result['transactionHash'],
            blockchain_type=blockchain_type,
            status='confirmed',
            details={
                'type': 'cast_vote',
                'election_id': election_id,
                'candidate_id': candidate_id,
                'voter': voter_address,
                'timestamp': result['timestamp']
            }
        )
        
        return JsonResponse({
            'success': True,
            'transaction_hash': result['transactionHash'],
            'block_number': result['blockNumber'],
            'timestamp': result['timestamp']
        })
        
    except Exception as e:
        logger.error(f"Error casting vote: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_election_results(request, election_id):
    """Get election results from blockchain"""
    try:
        blockchain_type = request.GET.get('blockchain', 'ETH')
        handler = get_blockchain_handler(blockchain_type)
        
        # Get results from blockchain
        results = handler.get_election_results(int(election_id))
        
        return JsonResponse({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error getting results: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@login_required
def check_vote_status(request, election_id):
    """Check if current user has voted"""
    try:
        blockchain_type = request.GET.get('blockchain', 'ETH')
        voter_address = request.GET.get('voter_address')
        
        if not voter_address:
            return JsonResponse({
                'success': False,
                'error': 'voter_address parameter required'
            }, status=400)
        
        handler = get_blockchain_handler(blockchain_type)
        has_voted = handler.has_user_voted(int(election_id), voter_address)
        
        vote_details = None
        if has_voted:
            vote_details = handler.get_voter_details(int(election_id), voter_address)
        
        return JsonResponse({
            'success': True,
            'has_voted': has_voted,
            'vote_details': vote_details
        })
        
    except Exception as e:
        logger.error(f"Error checking vote status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_transaction_status(request, tx_hash):
    """Get blockchain transaction status"""
    try:
        # Get from database first
        try:
            tx = BlockchainTransaction.objects.get(tx_hash=tx_hash)
            return JsonResponse({
                'success': True,
                'status': tx.status,
                'details': tx.details,
                'confirmations': tx.confirmations,
                'created_at': tx.created_at.isoformat()
            })
        except BlockchainTransaction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Transaction not found'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Error getting transaction status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)