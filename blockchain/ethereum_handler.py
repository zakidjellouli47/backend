from web3 import Web3
import json
import os
from dotenv import load_dotenv

load_dotenv()

class EthereumHandler:
    def __init__(self):
        # Connect to Ganache
        self.w3 = Web3(Web3.HTTPProvider(os.getenv('GANACHE_URL', 'http://127.0.0.1:7545')))
        
        # Load smart contract ABI and address
        with open(os.path.join(os.path.dirname(__file__), 'contracts/VotingSystem.json')) as f:
            contract_json = json.load(f)
        
        self.contract_abi = contract_json['abi']
        self.contract_address = os.getenv('CONTRACT_ADDRESS')
        
        # Create contract instance
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)
        
        # Default account for transactions
        self.default_account = self.w3.eth.accounts[0]
        
    def create_election(self, title, description, start_time, end_time):
        """Create a new election"""
        tx_hash = self.contract.functions.createElection(
            title, 
            description, 
            int(start_time.timestamp()), 
            int(end_time.timestamp())
        ).transact({'from': self.default_account})
        
        # Wait for transaction receipt
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get election ID from events
        election_created_event = self.contract.events.ElectionCreated().process_receipt(tx_receipt)
        if election_created_event:
            return election_created_event[0]['args']['electionId']
        return None
    
    def add_candidate(self, election_id, candidate_address, name):
        """Add a candidate to an election"""
        tx_hash = self.contract.functions.addCandidate(
            election_id,
            candidate_address,
            name
        ).transact({'from': self.default_account})
        
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)
    
    def cast_vote(self, election_id, candidate_id, voter_address):
        """Cast a vote in an election"""
        tx_hash = self.contract.functions.vote(
            election_id,
            candidate_id
        ).transact({'from': voter_address})
        
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)
    
    def get_election_details(self, election_id):
        """Get details of an election"""
        return self.contract.functions.getElection(election_id).call()
    
    def get_candidate_details(self, election_id, candidate_id):
        """Get details of a candidate"""
        return self.contract.functions.getCandidate(election_id, candidate_id).call()
    
    def get_election_results(self, election_id):
        """Get results of an election"""
        return self.contract.functions.getElectionResults(election_id).call()

