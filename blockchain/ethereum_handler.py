import os
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware

from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
import logging
# For Web3 v6+:




try:
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    # Continue with defaults

class EthereumHandler:
    def __init__(self):
        self.w3 = self._connect_to_network()
        self.contract = self._load_contract()
        self.logger = self._setup_logger()

    def _connect_to_network(self) -> Web3:
        """Establish connection to Ethereum network"""
        provider_url = os.getenv('ETH_PROVIDER_URL', 'http://localhost:7545')
        w3 = Web3(Web3.HTTPProvider(provider_url))
        
        if os.getenv('USE_POA', 'false').lower() == 'true':
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if not w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum network")
        return w3

    def _load_contract(self):
        """Load and instantiate the smart contract"""
        with open(os.path.join(os.path.dirname(__file__), 'contracts/voting.json')) as f:
            contract_abi = json.load(f)['abi']
        
        contract_address = os.getenv('CONTRACT_ADDRESS')
        if not contract_address:
            raise ValueError("CONTRACT_ADDRESS environment variable not set")
        
        return self.w3.eth.contract(address=contract_address, abi=contract_abi)

    def _setup_logger(self):
        """Configure logging"""
        logger = logging.getLogger('EthereumHandler')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _send_transaction(self, function_call, from_account: str = None) -> Dict[str, Any]:
        """Generic transaction sender with error handling"""
        if not from_account:
            from_account = self.w3.eth.accounts[0]
        
        try:
            tx_hash = function_call.transact({
                'from': from_account,
                'gas': 500000,
                'gasPrice': self.w3.to_wei('50', 'gwei')
            })
            return self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            self.logger.error(f"Transaction failed: {str(e)}")
            raise

    def create_election(self, title: str, description: str, 
                      start_time: int, end_time: int) -> Optional[int]:
        """Create a new election on blockchain"""
        try:
            receipt = self._send_transaction(
                self.contract.functions.createElection(
                    title, 
                    description, 
                    start_time, 
                    end_time
                )
            )
            
            event = self.contract.events.ElectionCreated().process_receipt(receipt)
            return event[0]['args']['electionId'] if event else None
        except Exception as e:
            self.logger.error(f"Failed to create election: {str(e)}")
            return None

    def add_candidate(self, election_id: int, 
                     candidate_address: str, name: str) -> Optional[int]:
        """Add candidate to an election"""
        try:
            receipt = self._send_transaction(
                self.contract.functions.addCandidate(
                    election_id,
                    candidate_address,
                    name
                )
            )
            
            event = self.contract.events.CandidateAdded().process_receipt(receipt)
            return event[0]['args']['candidateId'] if event else None
        except Exception as e:
            self.logger.error(f"Failed to add candidate: {str(e)}")
            return None

    def cast_vote(self, election_id: int, candidate_id: int, 
                 voter_address: str) -> bool:
        """Cast a vote in an election"""
        try:
            self._send_transaction(
                self.contract.functions.vote(election_id, candidate_id),
                from_account=voter_address
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to cast vote: {str(e)}")
            return False

    def get_election_details(self, election_id: int) -> Dict[str, Any]:
        """Get election details from blockchain"""
        try:
            return self.contract.functions.getElection(election_id).call()
        except Exception as e:
            self.logger.error(f"Failed to get election details: {str(e)}")
            return {}

    def get_election_results(self, election_id: int) -> Dict[str, List]:
        """Get final election results"""
        try:
            result = self.contract.functions.getElectionResults(election_id).call()
            return {
                'candidateIds': result[0],
                'names': result[1],
                'voteCounts': result[2]
            }
        except Exception as e:
            self.logger.error(f"Failed to get results: {str(e)}")
            return {'candidateIds': [], 'names': [], 'voteCounts': []}