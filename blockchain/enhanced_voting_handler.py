from web3 import Web3
import json
from django.conf import settings

class EnhancedVotingHandler:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.ETH_PROVIDER_URL))
        with open('contracts/VotingSystem.json') as f:
            contract_abi = json.load(f)['abi']
        self.contract = self.w3.eth.contract(
            address=settings.CONTRACT_ADDRESS,
            abi=contract_abi
        )
    
    def get_voter_details(self, election_id, voter_address):
        return self.contract.functions.getVoterDetails(
            election_id,
            voter_address
        ).call()
    
    def get_complete_results(self, election_id):
        return self.contract.functions.getElectionResults(
            election_id
        ).call()
    
    def get_votes_by_candidate(self, election_id, candidate_id):
        return self.contract.functions.getVotesByCandidate(
            election_id,
            candidate_id
        ).call()