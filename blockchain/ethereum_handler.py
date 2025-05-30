import os
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import ContractLogicError, TransactionNotFound
from typing import Optional, Dict, Any, List, Tuple
import logging
from datetime import datetime
from functools import wraps
import time

# Enhanced logger configuration
logger = logging.getLogger('EnhancedEthereumHandler')
logger.setLevel(logging.INFO)

# Create handlers
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler('ethereum_handler.log')
c_handler.setLevel(logging.WARNING)
f_handler.setLevel(logging.INFO)

# Create formatters and add to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(formatter)
f_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)

def handle_contract_errors(func):
    """Decorator to handle common contract errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ContractLogicError as e:
            logger.error(f"Contract logic error in {func.__name__}: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Value error in {func.__name__}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise
    return wrapper

class EnhancedEthereumHandler:
    def __init__(self, provider_url: Optional[str] = None, contract_address: Optional[str] = None):
        """
        Initialize Ethereum handler with optional override of env vars
        
        Args:
            provider_url: Optional override for ETH_PROVIDER_URL
            contract_address: Optional override for CONTRACT_ADDRESS
        """
        self.w3 = self._connect_to_network(provider_url)
        self.contract = self._load_contract(contract_address)
        self._validate_contract()

    def _connect_to_network(self, provider_url: Optional[str] = None) -> Web3:
        """Establish robust connection to Ethereum network"""
        url = provider_url or os.getenv('ETH_PROVIDER_URL', 'http://localhost:7545')
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 60}))
                
                if os.getenv('USE_POA', 'false').lower() == 'true':
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                if not w3.is_connected():
                    raise ConnectionError(f"Failed to connect to Ethereum node at {url}")
                
                logger.info(f"Successfully connected to Ethereum network (Chain ID: {w3.eth.chain_id})")
                return w3
            
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.critical(f"Failed to connect after {max_retries} attempts")
                    raise
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                time.sleep(retry_delay)

    def _load_contract(self, contract_address: Optional[str] = None) -> Any:
        """Load and validate the smart contract"""
        contract_path = os.path.join(os.path.dirname(__file__), 'contracts/voting.json')
        
        try:
            with open(contract_path) as f:
                contract_data = json.load(f)
                abi = contract_data['abi']
                
                # Use provided address or fall back to env var
                address = contract_address or os.getenv('CONTRACT_ADDRESS')
                if not address:
                    raise ValueError("No contract address provided and CONTRACT_ADDRESS env var not set")
                
                if not self.w3.is_address(address):
                    raise ValueError(f"Invalid contract address: {address}")
                
                contract = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(address),
                    abi=abi
                )
                
                logger.info(f"Successfully loaded contract at {address}")
                return contract
                
        except FileNotFoundError:
            logger.error(f"Contract file not found at {contract_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in contract file at {contract_path}")
            raise

    def _validate_contract(self) -> None:
        """Validate that contract has required functions"""
        required_functions = {
            'createElection': 4,
            'addCandidate': 3,
            'vote': 2,
            'getElection': 1,
            'getElectionResults': 1,
            'hasUserVoted': 2
        }
        
        missing = []
        for func, params in required_functions.items():
            if not hasattr(self.contract.functions, func):
                missing.append(func)
        
        if missing:
            raise ValueError(f"Contract is missing required functions: {', '.join(missing)}")

    @handle_contract_errors
    def _send_transaction(self, function_call, from_account: str, value: int = 0, 
                         gas: int = 500000, gas_price: Optional[int] = None) -> Dict[str, Any]:
        """
        Enhanced transaction sender with retries and better gas handling
        
        Args:
            function_call: The contract function call
            from_account: Account to send from
            value: Ether value to send (in wei)
            gas: Gas limit
            gas_price: Optional gas price in wei
            
        Returns:
            Transaction receipt
        """
        if not self.w3.is_address(from_account):
            raise ValueError(f"Invalid from_account address: {from_account}")
            
        tx_params = {
            'from': self.w3.to_checksum_address(from_account),
            'value': value,
            'gas': gas,
            'nonce': self.w3.eth.get_transaction_count(from_account),
        }
        
        # Gas price strategy
        if gas_price:
            tx_params['gasPrice'] = gas_price
        else:
            try:
                tx_params['gasPrice'] = self.w3.eth.generate_gas_price() or self.w3.to_wei('50', 'gwei')
            except:
                tx_params['gasPrice'] = self.w3.to_wei('50', 'gwei')
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                tx_hash = function_call.transact(tx_params)
                return self._wait_for_transaction(tx_hash)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Transaction failed after {max_retries} attempts")
                    raise
                logger.warning(f"Transaction attempt {attempt + 1} failed: {str(e)}")
                time.sleep(2)

    def _wait_for_transaction(self, tx_hash: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for transaction receipt with timeout and logging"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    if receipt['status'] == 1:
                        logger.info(f"Transaction {tx_hash.hex()} confirmed in block {receipt['blockNumber']}")
                        return receipt
                    else:
                        raise ContractLogicError(f"Transaction {tx_hash.hex()} failed")
                time.sleep(2)
            except TransactionNotFound:
                time.sleep(2)
        raise TimeoutError(f"Transaction {tx_hash.hex()} not confirmed after {timeout} seconds")

    @handle_contract_errors
    def create_election(self, title: str, description: str, 
                       start_time: int, end_time: int, 
                       creator_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Enhanced election creation with full receipt handling
        
        Args:
            title: Election title
            description: Election description
            start_time: Unix timestamp
            end_time: Unix timestamp
            creator_address: Optional creator address
            
        Returns:
            Dictionary containing electionId and transaction details
        """
        if start_time >= end_time:
            raise ValueError("End time must be after start time")
        if start_time < int(time.time()):
            raise ValueError("Start time cannot be in the past")
            
        creator = creator_address or self.w3.eth.accounts[0]
        
        receipt = self._send_transaction(
            function_call=self.contract.functions.createElection(
                title, description, start_time, end_time
            ),
            from_account=creator
        )
        
        event = self.contract.events.ElectionCreated().process_receipt(receipt)
        if not event:
            raise ValueError("No ElectionCreated event found in receipt")
            
        return {
            'electionId': event[0]['args']['electionId'],
            'transactionHash': receipt['transactionHash'].hex(),
            'blockNumber': receipt['blockNumber'],
            'gasUsed': receipt['gasUsed']
        }

    @handle_contract_errors
    def add_candidate(self, election_id: int, candidate_address: str, 
                     name: str, caller_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Add candidate with enhanced validation
        
        Args:
            election_id: The election ID
            candidate_address: Candidate's Ethereum address
            name: Candidate name
            caller_address: Optional caller address
            
        Returns:
            Dictionary containing candidateId and transaction details
        """
        if not self.w3.is_address(candidate_address):
            raise ValueError("Invalid candidate address")
            
        caller = caller_address or self.w3.eth.accounts[0]
        
        receipt = self._send_transaction(
            function_call=self.contract.functions.addCandidate(
                election_id, candidate_address, name
            ),
            from_account=caller
        )
        
        event = self.contract.events.CandidateAdded().process_receipt(receipt)
        if not event:
            raise ValueError("No CandidateAdded event found in receipt")
            
        return {
            'candidateId': event[0]['args']['candidateId'],
            'transactionHash': receipt['transactionHash'].hex(),
            'blockNumber': receipt['blockNumber']
        }

    @handle_contract_errors
    def cast_vote(self, election_id: int, candidate_id: int, 
                  voter_address: str) -> Dict[str, Any]:
        """
        Enhanced vote casting with proof generation
        
        Args:
            election_id: The election ID
            candidate_id: The candidate ID
            voter_address: Voter's Ethereum address
            
        Returns:
            Dictionary containing vote receipt details
        """
        if not self.w3.is_address(voter_address):
            raise ValueError("Invalid voter address")
            
        # Check if already voted
        if self.has_user_voted(election_id, voter_address):
            raise ValueError("Voter has already voted in this election")
            
        receipt = self._send_transaction(
            function_call=self.contract.functions.vote(election_id, candidate_id),
            from_account=voter_address,
            gas=300000  # Higher gas limit for voting
        )
        
        # Get vote timestamp from block
        block = self.w3.eth.get_block(receipt['blockNumber'])
        
        return {
            'transactionHash': receipt['transactionHash'].hex(),
            'blockNumber': receipt['blockNumber'],
            'timestamp': block['timestamp'],
            'gasUsed': receipt['gasUsed']
        }

    @handle_contract_errors
    def get_election_details(self, election_id: int) -> Dict[str, Any]:
        """Get enhanced election details with status"""
        details = self.contract.functions.getElection(election_id).call()
        
        current_time = int(time.time())
        status = "pending"
        if current_time >= details[3]:  # start_time
            status = "active" if current_time <= details[4] else "ended"  # end_time
            
        return {
            'id': details[0],
            'title': details[1],
            'description': details[2],
            'startTime': details[3],
            'endTime': details[4],
            'creator': details[5],
            'status': status
        }

    @handle_contract_errors
    def get_election_results(self, election_id: int) -> Dict[str, Any]:
        """Get comprehensive election results with percentages"""
        result = self.contract.functions.getElectionResults(election_id).call()
        
        total_votes = sum(result[2])
        candidates = []
        for i in range(len(result[0])):
            vote_count = result[2][i]
            candidates.append({
                'id': result[0][i],
                'name': result[1][i],
                'votes': vote_count,
                'percentage': (vote_count / total_votes) * 100 if total_votes > 0 else 0
            })
            
        return {
            'candidates': candidates,
            'totalVotes': total_votes,
            'timestamp': int(time.time())
        }

    @handle_contract_errors
    def has_user_voted(self, election_id: int, voter_address: str) -> bool:
        """Check if user has voted with address validation"""
        if not self.w3.is_address(voter_address):
            raise ValueError("Invalid voter address")
        return self.contract.functions.hasUserVoted(election_id, voter_address).call()

    @handle_contract_errors
    def get_voter_details(self, election_id: int, voter_address: str) -> Optional[Dict[str, Any]]:
        """Get detailed voting information for a specific voter"""
        if not self.has_user_voted(election_id, voter_address):
            return None
            
        event_filter = self.contract.events.VoteCast.createFilter(
            fromBlock=0,
            argument_filters={
                'electionId': election_id,
                'voter': voter_address
            }
        )
        votes = event_filter.get_all_entries()
        
        if not votes:
            return None
            
        vote = votes[0]
        block = self.w3.eth.get_block(vote['blockNumber'])
        
        return {
            'electionId': vote['args']['electionId'],
            'candidateId': vote['args']['candidateId'],
            'timestamp': block['timestamp'],
            'blockNumber': vote['blockNumber'],
            'transactionHash': vote['transactionHash'].hex()
        }

    @handle_contract_errors
    def get_all_votes(self, election_id: int) -> List[Dict[str, Any]]:
        """Get all votes for an election with timestamps"""
        event_filter = self.contract.events.VoteCast.createFilter(
            fromBlock=0,
            argument_filters={'electionId': election_id}
        )
        votes = event_filter.get_all_entries()
        
        result = []
        for vote in votes:
            block = self.w3.eth.get_block(vote['blockNumber'])
            result.append({
                'voter': vote['args']['voter'],
                'candidateId': vote['args']['candidateId'],
                'timestamp': block['timestamp'],
                'blockNumber': vote['blockNumber'],
                'transactionHash': vote['transactionHash'].hex()
            })
            
        return result