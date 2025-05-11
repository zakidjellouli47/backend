import os
import subprocess
import json
import logging
from typing import Optional, Dict, Any, List

class HyperledgerHandler:
    def __init__(self):
        self.network_path = os.getenv('HLF_NETWORK_PATH', '/opt/gopath/src/github.com/hyperledger/fabric/network')
        self.chaincode_name = 'voting'
        self.channel_name = 'votingchannel'
        self.logger = self._setup_logger()
        self._verify_environment()

    def _setup_logger(self):
        logger = logging.getLogger('HyperledgerHandler')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _verify_environment(self):
        """Verify required environment variables are set"""
        required_vars = ['CORE_PEER_MSPCONFIGPATH', 'CORE_PEER_ADDRESS']
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    def _execute_command(self, command: List[str]) -> Optional[Dict[str, Any]]:
        """Execute shell command with error handling"""
        try:
            result = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {'output': result.stdout.strip()}
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e.stderr}")
            return None

    def create_election(self, title: str, description: str, 
                       start_time: int, end_time: int) -> bool:
        """Create election on Hyperledger network"""
        args = [title, description, str(start_time), str(end_time)]
        return self._invoke_chaincode('CreateElection', args) is not None

    def _invoke_chaincode(self, function: str, args: List[str]) -> Optional[Dict[str, Any]]:
        """Generic chaincode invoker"""
        command = [
            'peer', 'chaincode', 'invoke',
            '-o', 'orderer.example.com:7050',
            '--tls',
            '--cafile', '/opt/gopath/src/github.com/hyperledger/fabric/network/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem',
            '-C', self.channel_name,
            '-n', self.chaincode_name,
            '-c', json.dumps({'function': function, 'Args': args})
        ]
        return self._execute_command(command)

    def _query_chaincode(self, function: str, args: List[str]) -> Optional[Dict[str, Any]]:
        """Generic chaincode querier"""
        command = [
            'peer', 'chaincode', 'query',
            '-C', self.channel_name,
            '-n', self.chaincode_name,
            '-c', json.dumps({'function': function, 'Args': args})
        ]
        return self._execute_command(command)

    def get_election(self, election_id: str) -> Optional[Dict[str, Any]]:
        """Get election details"""
        return self._query_chaincode('GetElection', [election_id])

    def get_election_results(self, election_id: str) -> Optional[Dict[str, Any]]:
        """Get election results"""
        return self._query_chaincode('GetResults', [election_id])

    def deploy_chaincode(self) -> bool:
        """Deploy chaincode to network (admin only)"""
        commands = [
            ['peer', 'lifecycle', 'chaincode', 'package', 'voting.tar.gz',
             '--path', '/opt/gopath/src/github.com/chaincode/voting',
             '--lang', 'golang',
             '--label', 'voting_1'],
            ['peer', 'lifecycle', 'chaincode', 'install', 'voting.tar.gz'],
            ['peer', 'lifecycle', 'chaincode', 'approveformyorg',
             '-o', 'orderer.example.com:7050',
             '--channelID', self.channel_name,
             '--name', self.chaincode_name,
             '--version', '1.0',
             '--package-id', 'voting_1',
             '--sequence', '1',
             '--tls',
             '--cafile', '/opt/gopath/src/github.com/hyperledger/fabric/network/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem'],
            ['peer', 'lifecycle', 'chaincode', 'commit',
             '-o', 'orderer.example.com:7050',
             '--channelID', self.channel_name,
             '--name', self.chaincode_name,
             '--version', '1.0',
             '--sequence', '1',
             '--tls',
             '--cafile', '/opt/gopath/src/github.com/hyperledger/fabric/network/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem']
        ]
        
        for cmd in commands:
            if not self._execute_command(cmd):
                return False
        return True