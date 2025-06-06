# voting/election_coordinator.py
"""
Election Coordinator - Orchestrates blockchain operations with business logic
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

from blockchain.ethereum_handler import EnhancedEthereumHandler
from blockchain.models import BlockchainTransaction

logger = logging.getLogger(__name__)

class ElectionCoordinator:
    """Coordinates election operations across blockchain and IPFS"""
    
    def __init__(self, blockchain_type: str = 'ETH'):
        self.blockchain_type = blockchain_type
        self.handler = self._get_blockchain_handler()
    
    def _get_blockchain_handler(self):
        """Get the appropriate blockchain handler"""
        if self.blockchain_type == 'ETH':
            return EnhancedEthereumHandler()
        elif self.blockchain_type == 'HLF':
            # When you implement Hyperledger
            raise NotImplementedError("Hyperledger support coming soon")
        else:
            raise ValueError(f"Unsupported blockchain: {self.blockchain_type}")
    
    def create_election_with_validation(self, election_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create election with comprehensive validation and IPFS metadata storage
        """
        # Validate election data
        validation_errors = self._validate_election_data(election_data)
        if validation_errors:
            raise ValueError(f"Validation errors: {', '.join(validation_errors)}")
        
        # Create on blockchain
        blockchain_result = self.handler.create_election(
            title=election_data['title'],
            description=election_data['description'],
            start_time=election_data['start_time'],
            end_time=election_data['end_time'],
            creator_address=election_data['creator_address']
        )
        
        # Store additional metadata on IPFS if needed
        # ipfs_hash = self._store_election_metadata_on_ipfs(election_data)
        
        # Track transaction
        tx_record = BlockchainTransaction.objects.create(
            tx_hash=blockchain_result['transactionHash'],
            blockchain_type=self.blockchain_type,
            status='confirmed',
            details={
                'type': 'create_election',
                'election_id': blockchain_result['electionId'],
                'title': election_data['title'],
                'creator': election_data['creator_address'],
                # 'ipfs_hash': ipfs_hash  # When IPFS is integrated
            }
        )
        
        return {
            'success': True,
            'election_id': blockchain_result['electionId'],
            'transaction_hash': blockchain_result['transactionHash'],
            'block_number': blockchain_result['blockNumber'],
            'gas_used': blockchain_result['gasUsed']
        }
    
    def add_candidate_with_verification(self, election_id: int, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add candidate with eligibility verification
        """
        # Verify election is still in registration phase
        election_details = self.handler.get_election_details(election_id)
        current_time = int(datetime.now(timezone.utc).timestamp())
        
        if current_time >= election_details['startTime']:
            raise ValueError("Cannot add candidates after election has started")
        
        # Verify candidate eligibility (implement your business rules)
        if not self._is_candidate_eligible(candidate_data['candidate_address'], election_id):
            raise ValueError("Candidate is not eligible for this election")
        
        # Add to blockchain
        result = self.handler.add_candidate(
            election_id=election_id,
            candidate_address=candidate_data['candidate_address'],
            name=candidate_data['candidate_name'],
            caller_address=candidate_data.get('caller_address')
        )
        
        # Store candidate profile on IPFS if provided
        # if candidate_data.get('bio') or candidate_data.get('manifesto'):
        #     ipfs_hash = self._store_candidate_profile_on_ipfs(candidate_data)
        
        # Track transaction
        BlockchainTransaction.objects.create(
            tx_hash=result['transactionHash'],
            blockchain_type=self.blockchain_type,
            status='confirmed',
            details={
                'type': 'add_candidate',
                'election_id': election_id,
                'candidate_id': result['candidateId'],
                'candidate_address': candidate_data['candidate_address'],
                'candidate_name': candidate_data['candidate_name']
            }
        )
        
        return {
            'success': True,
            'candidate_id': result['candidateId'],
            'transaction_hash': result['transactionHash']
        }
    
    def cast_vote_with_validation(self, election_id: int, vote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cast vote with comprehensive validation
        """
        voter_address = vote_data['voter_address']
        candidate_id = vote_data['candidate_id']
        
        # Validate voting eligibility
        validation_result = self._validate_vote_eligibility(election_id, voter_address)
        if not validation_result['eligible']:
            raise ValueError(validation_result['reason'])
        
        # Verify election is active
        election_details = self.handler.get_election_details(election_id)
        if election_details['status'] != 'active':
            raise ValueError(f"Election is {election_details['status']}, voting not allowed")
        
        # Cast vote on blockchain
        result = self.handler.cast_vote(
            election_id=election_id,
            candidate_id=candidate_id,
            voter_address=voter_address
        )
        
        # Track vote transaction
        BlockchainTransaction.objects.create(
            tx_hash=result['transactionHash'],
            blockchain_type=self.blockchain_type,
            status='confirmed',
            details={
                'type': 'cast_vote',
                'election_id': election_id,
                'candidate_id': candidate_id,
                'voter': voter_address,
                'timestamp': result['timestamp'],
                'block_number': result['blockNumber']
            }
        )
        
        return {
            'success': True,
            'transaction_hash': result['transactionHash'],
            'block_number': result['blockNumber'],
            'timestamp': result['timestamp'],
            'vote_confirmed': True
        }
    
    def get_comprehensive_results(self, election_id: int) -> Dict[str, Any]:
        """
        Get comprehensive election results with analytics
        """
        # Get basic results from blockchain
        results = self.handler.get_election_results(election_id)
        election_details = self.handler.get_election_details(election_id)
        
        # Add additional analytics
        total_votes = results['totalVotes']
        winner = None
        if total_votes > 0:
            winner = max(results['candidates'], key=lambda x: x['votes'])
        
        # Get voting timeline (all votes with timestamps)
        vote_timeline = self.handler.get_all_votes(election_id)
        
        return {
            'election': election_details,
            'results': results,
            'winner': winner,
            'vote_timeline': vote_timeline,
            'analytics': {
                'total_votes': total_votes,
                'turnout_percentage': self._calculate_turnout(election_id, total_votes),
                'voting_distribution': self._analyze_voting_pattern(vote_timeline)
            }
        }
    
    def _validate_election_data(self, election_data: Dict[str, Any]) -> List[str]:
        """Validate election creation data"""
        errors = []
        
        required_fields = ['title', 'description', 'start_time', 'end_time', 'creator_address']
        for field in required_fields:
            if not election_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        if election_data.get('start_time') and election_data.get('end_time'):
            if election_data['start_time'] >= election_data['end_time']:
                errors.append("End time must be after start time")
            
            current_time = int(datetime.now(timezone.utc).timestamp())
            if election_data['start_time'] <= current_time:
                errors.append("Start time must be in the future")
        
        return errors
    
    def _validate_vote_eligibility(self, election_id: int, voter_address: str) -> Dict[str, Any]:
        """Validate if voter is eligible to vote"""
        
        # Check if already voted
        if self.handler.has_user_voted(election_id, voter_address):
            return {
                'eligible': False,
                'reason': 'Voter has already voted in this election'
            }
        
        # Add more eligibility checks here based on your business rules
        # - Age verification
        # - Registration status
        # - Geographic restrictions
        # etc.
        
        return {'eligible': True, 'reason': None}
    
    def _is_candidate_eligible(self, candidate_address: str, election_id: int) -> bool:
        """Check if candidate is eligible for this election"""
        # Implement your candidate eligibility rules
        # - Age requirements
        # - Residency requirements
        # - Registration status
        # - Criminal background checks
        # etc.
        
        return True  # Placeholder
    
    def _calculate_turnout(self, election_id: int, total_votes: int) -> float:
        """Calculate voter turnout percentage"""
        # You'll need to implement logic to get total eligible voters
        # This could come from your authentication system or a separate registry
        
        total_eligible_voters = 1000  # Placeholder
        return (total_votes / total_eligible_voters) * 100 if total_eligible_voters > 0 else 0
    
    def _analyze_voting_pattern(self, vote_timeline: List[Dict]) -> Dict[str, Any]:
        """Analyze voting patterns over time"""
        if not vote_timeline:
            return {}
        
        # Group votes by hour/day for pattern analysis
        hourly_votes = {}
        for vote in vote_timeline:
            hour = datetime.fromtimestamp(vote['timestamp']).strftime('%Y-%m-%d %H:00')
            hourly_votes[hour] = hourly_votes.get(hour, 0) + 1
        
        return {
            'hourly_distribution': hourly_votes,
            'peak_voting_hour': max(hourly_votes.items(), key=lambda x: x[1]) if hourly_votes else None,
            'total_voting_sessions': len(vote_timeline)
        }