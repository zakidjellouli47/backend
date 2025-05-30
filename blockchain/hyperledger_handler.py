import os
import subprocess
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import time
from functools import wraps

# Configure advanced logging
logger = logging.getLogger('EnhancedHyperledgerHandler')
logger.setLevel(logging.INFO)

# Create handlers
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler('hyperledger_handler.log')
c_handler.setLevel(logging.WARNING)
f_handler.setLevel(logging.INFO)

# Create formatters
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(formatter)
f_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(c_handler)
logger.addHandler(f_handler)

def handle_fabric_errors(func):
    """Decorator to handle Fabric-specific errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except subprocess.CalledProcessError as e:
            logger.error(f"Fabric command failed in {func.__name__}: {e.stderr}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response in {func.__name__}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise
    return wrapper

class EnhancedHyperledgerHandler:
    def __init__(self, network_path: Optional[str] = None, channel_name: Optional[str] = None):
        """
        Initialize with optional overrides for environment variables
        
        Args:
            network_path: Path to Fabric network (overrides HLF_NETWORK_PATH)
            channel_name: Channel name (overrides CHANNEL_NAME)
        """
        # Use mounted path as default instead of hardcoded path
        self.network_path = network_path or os.getenv('HLF_NETWORK_PATH', '/hyperledger')
        self.channel_name = channel_name or os.getenv('CHANNEL_NAME', 'mychannel')
        self.chaincode_name = os.getenv('CHAINCODE_NAME', 'voting')
        
        # Get other environment variables
        self.peer_address = os.getenv('CORE_PEER_ADDRESS', 'host.docker.internal:7051')
        self.orderer_address = os.getenv('ORDERER_ADDRESS', 'host.docker.internal:7050')
        self.msp_config_path = os.getenv('CORE_PEER_MSPCONFIGPATH')
        self.tls_root_cert = os.getenv('CORE_PEER_TLS_ROOTCERT_FILE')
        self.orderer_ca = os.getenv('ORDERER_CA')
        self.msp_id = os.getenv('CORE_PEER_LOCALMSPID', 'Org1MSP')
        self.tls_enabled = os.getenv('CORE_PEER_TLS_ENABLED', 'true').lower() == 'true'
        
        self._verify_environment()
        self._verify_network_access()

    def _verify_environment(self):
        """Validate all required environment variables"""
        required_vars = [
            'CORE_PEER_MSPCONFIGPATH',
            'CORE_PEER_ADDRESS',
            'ORDERER_CA',
            'CORE_PEER_TLS_ROOTCERT_FILE'
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    def _verify_network_access(self):
        """Verify we can access the network components"""
        if not os.path.exists(self.network_path):
            logger.warning(f"Network path not found: {self.network_path}")
            # Don't raise error immediately, try to continue with cert verification
        
        # Check if required certificates exist
        cert_paths_to_check = [
            self.msp_config_path,
            self.tls_root_cert,
            self.orderer_ca
        ]
        
        missing_certs = []
        for cert_path in cert_paths_to_check:
            if cert_path and not os.path.exists(cert_path):
                missing_certs.append(cert_path)
        
        if missing_certs:
            raise FileNotFoundError(f"Missing certificate files: {', '.join(missing_certs)}")
        
        # Check for network directories only if network path exists
        if os.path.exists(self.network_path):
            required_dirs = [
                'organizations'
            ]
            for dir_name in required_dirs:
                dir_path = os.path.join(self.network_path, dir_name)
                if not os.path.exists(dir_path):
                    logger.warning(f"Missing network directory: {dir_path}")

    @handle_fabric_errors
    def _execute_command(self, command: List[str], retries: int = 3, delay: int = 2) -> Dict[str, Any]:
        """
        Enhanced command execution with retries and timeout handling
        
        Args:
            command: The command to execute
            retries: Number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            Parsed JSON response or raw output
        """
        # Set environment variables for peer command
        env = os.environ.copy()
        env.update({
            'CORE_PEER_MSPCONFIGPATH': self.msp_config_path,
            'CORE_PEER_ADDRESS': self.peer_address,
            'CORE_PEER_LOCALMSPID': self.msp_id,
            'CORE_PEER_TLS_ENABLED': 'true' if self.tls_enabled else 'false',
            'CORE_PEER_TLS_ROOTCERT_FILE': self.tls_root_cert
        })
        
        full_command = [
            'peer', 'chaincode', *command,
            '--tls' if self.tls_enabled else '--no-tls',
            '--cafile', self.orderer_ca
        ]
        
        for attempt in range(retries):
            try:
                result = subprocess.run(
                    full_command,
                    cwd=self.network_path if os.path.exists(self.network_path) else '/app',
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,  # 30 second timeout
                    env=env
                )
                
                # Try to parse JSON, fall back to raw output
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {'output': result.stdout.strip()}
                    
            except subprocess.TimeoutExpired:
                if attempt == retries - 1:
                    logger.error(f"Command timed out after {retries} attempts")
                    raise
                logger.warning(f"Command timeout, retrying... (Attempt {attempt + 1}/{retries})")
                time.sleep(delay)
            except subprocess.CalledProcessError as e:
                if attempt == retries - 1:
                    logger.error(f"Command failed after {retries} attempts: {e.stderr}")
                    raise
                logger.warning(f"Command failed, retrying... (Attempt {attempt + 1}/{retries})")
                time.sleep(delay)

    @handle_fabric_errors
    def create_election(self, title: str, description: str, 
                       start_time: int, end_time: int, 
                       creator_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new election with enhanced metadata
        
        Args:
            title: Election title
            description: Election description
            start_time: Unix timestamp
            end_time: Unix timestamp
            creator_id: Optional creator identity
            
        Returns:
            Election creation details
        """
        if start_time >= end_time:
            raise ValueError("End time must be after start time")
        if start_time < int(time.time()):
            raise ValueError("Start time cannot be in the past")
            
        response = self._invoke_chaincode(
            'CreateElection',
            [title, description, str(start_time), str(end_time), creator_id or '']
        )
        
        if not response or 'electionId' not in response:
            raise ValueError("Failed to parse election ID from response")
            
        return {
            'electionId': response['electionId'],
            'transactionId': response.get('transactionId', ''),
            'timestamp': int(time.time())
        }

    @handle_fabric_errors
    def add_candidate(self, election_id: str, candidate_id: str, 
                     name: str, caller_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add candidate to election with validation
        
        Args:
            election_id: The election ID
            candidate_id: Candidate's unique identifier
            name: Candidate name
            caller_id: Optional caller identity
            
        Returns:
            Candidate addition details
        """
        if not candidate_id or not name:
            raise ValueError("Candidate ID and name are required")
            
        response = self._invoke_chaincode(
            'AddCandidate',
            [election_id, candidate_id, name, caller_id or '']
        )
        
        return {
            'candidateId': candidate_id,
            'transactionId': response.get('transactionId', ''),
            'timestamp': int(time.time())
        }

    @handle_fabric_errors
    def cast_vote(self, election_id: str, candidate_id: str, 
                  voter_id: str) -> Dict[str, Any]:
        """
        Cast vote with comprehensive validation
        
        Args:
            election_id: The election ID
            candidate_id: The candidate ID
            voter_id: Voter's unique identity
            
        Returns:
            Vote receipt details
        """
        # Check if already voted
        if self.has_user_voted(election_id, voter_id):
            raise ValueError("Voter has already voted in this election")
            
        response = self._invoke_chaincode(
            'CastVote',
            [election_id, candidate_id, voter_id, str(int(time.time()))]
        )
        
        return {
            'electionId': election_id,
            'candidateId': candidate_id,
            'transactionId': response.get('transactionId', ''),
            'timestamp': int(time.time())
        }

    @handle_fabric_errors
    def get_election_details(self, election_id: str) -> Dict[str, Any]:
        """Get enhanced election details with status"""
        response = self._query_chaincode('GetElection', [election_id])
        
        current_time = int(time.time())
        status = "pending"
        if current_time >= response['startTime']:
            status = "active" if current_time <= response['endTime'] else "ended"
            
        return {
            'id': response['electionId'],
            'title': response['title'],
            'description': response['description'],
            'startTime': response['startTime'],
            'endTime': response['endTime'],
            'creator': response['creator'],
            'status': status,
            'candidateCount': response.get('candidateCount', 0)
        }

    @handle_fabric_errors
    def get_election_results(self, election_id: str) -> Dict[str, Any]:
        """Get comprehensive election results with percentages"""
        response = self._query_chaincode('GetResults', [election_id])
        
        total_votes = sum(c['votes'] for c in response['candidates'])
        candidates = []
        for candidate in response['candidates']:
            candidates.append({
                'id': candidate['id'],
                'name': candidate['name'],
                'votes': candidate['votes'],
                'percentage': (candidate['votes'] / total_votes) * 100 if total_votes > 0 else 0
            })
            
        return {
            'candidates': candidates,
            'totalVotes': total_votes,
            'timestamp': int(time.time())
        }

    @handle_fabric_errors
    def has_user_voted(self, election_id: str, voter_id: str) -> bool:
        """Check if user has voted"""
        response = self._query_chaincode('HasVoted', [election_id, voter_id])
        return response.get('hasVoted', False)

    @handle_fabric_errors
    def get_voter_details(self, election_id: str, voter_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed voting information for a specific voter"""
        if not self.has_user_voted(election_id, voter_id):
            return None
            
        response = self._query_chaincode('GetVoterDetails', [election_id, voter_id])
        return {
            'electionId': response['electionId'],
            'candidateId': response['candidateId'],
            'timestamp': response['timestamp'],
            'transactionId': response.get('transactionId', '')
        }

    @handle_fabric_errors
    def get_all_votes(self, election_id: str) -> List[Dict[str, Any]]:
        """Get all votes for an election with timestamps"""
        response = self._query_chaincode('GetAllVotes', [election_id])
        return response.get('votes', [])

    def _invoke_chaincode(self, function: str, args: List[str]) -> Dict[str, Any]:
        """Generic chaincode invocation with enhanced error handling"""
        command = [
            'invoke',
            '-o', self.orderer_address,
            '-C', self.channel_name,
            '-n', self.chaincode_name,
            '-c', json.dumps({'function': function, 'Args': args})
        ]
        return self._execute_command(command)

    def _query_chaincode(self, function: str, args: List[str]) -> Dict[str, Any]:
        """Generic chaincode query with enhanced error handling"""
        command = [
            'query',
            '-C', self.channel_name,
            '-n', self.chaincode_name,
            '-c', json.dumps({'function': function, 'Args': args})
        ]
        return self._execute_command(command)

    @handle_fabric_errors
    def deploy_chaincode(self, version: str = "1.0", sequence: int = 1, 
                        path: Optional[str] = None) -> bool:
        """
        Enhanced chaincode deployment with version control
        
        Args:
            version: Chaincode version
            sequence: Deployment sequence number
            path: Path to chaincode (defaults to standard location)
        """
        cc_path = path or '/opt/gopath/src/github.com/chaincode/voting'
        label = f"{self.chaincode_name}_{version.replace('.', '_')}"
        
        commands = [
            ['lifecycle', 'chaincode', 'package', f"{self.chaincode_name}.tar.gz",
             '--path', cc_path,
             '--lang', 'golang',
             '--label', label],
             
            ['lifecycle', 'chaincode', 'install', f"{self.chaincode_name}.tar.gz"],
            
            ['lifecycle', 'chaincode', 'approveformyorg',
             '-o', self.orderer_address,
             '--channelID', self.channel_name,
             '--name', self.chaincode_name,
             '--version', version,
             '--package-id', label,
             '--sequence', str(sequence)],
             
            ['lifecycle', 'chaincode', 'commit',
             '-o', self.orderer_address,
             '--channelID', self.channel_name,
             '--name', self.chaincode_name,
             '--version', version,
             '--sequence', str(sequence)]
        ]
        
        for cmd in commands:
            result = self._execute_command(cmd)
            if not result or 'error' in result:
                logger.error(f"Deployment step failed: {cmd}")
                return False
                
        logger.info(f"Successfully deployed chaincode {self.chaincode_name} v{version}")
        return True