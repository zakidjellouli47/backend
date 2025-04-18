# blockchain/hyperledger_handler.py
import os
import subprocess
import json
import datetime
import re

class HyperledgerHandler:
    def __init__(self):
        # Path to Hyperledger Fabric binaries and configuration
        self.fabric_path = os.path.expanduser("~/hyperledger-fabric/fabric-samples")
        self.network_path = os.path.join(self.fabric_path, "test-network")
        self.chaincode_path = os.path.join(self.fabric_path, "chaincode/voting")
        
        # Set environment variables for Org1 by default
        self._set_org1_env()
    
    def _set_org1_env(self):
        """Set environment variables for Org1"""
        os.environ["FABRIC_CFG_PATH"] = os.path.join(self.fabric_path, "config/")
        os.environ["CORE_PEER_TLS_ENABLED"] = "true"
        os.environ["CORE_PEER_LOCALMSPID"] = "Org1MSP"
        os.environ["CORE_PEER_TLS_ROOTCERT_FILE"] = os.path.join(
            self.network_path, 
            "organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
        )
        os.environ["CORE_PEER_MSPCONFIGPATH"] = os.path.join(
            self.network_path,
            "organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
        )
        os.environ["CORE_PEER_ADDRESS"] = "localhost:7051"
    
    def _set_org2_env(self):
        """Set environment variables for Org2"""
        os.environ["CORE_PEER_LOCALMSPID"] = "Org2MSP"
        os.environ["CORE_PEER_TLS_ROOTCERT_FILE"] = os.path.join(
            self.network_path, 
            "organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt"
        )
        os.environ["CORE_PEER_MSPCONFIGPATH"] = os.path.join(
            self.network_path,
            "organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp"
        )
        os.environ["CORE_PEER_ADDRESS"] = "localhost:9051"
        
    def start_network(self):
        """Start the Hyperledger Fabric network"""
        try:
            os.chdir(self.network_path)
            subprocess.run(["./network.sh", "up", "createChannel", "-c", "votingchannel"], check=True)
            print("Network started successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error starting network: {e}")
            return False
        
    def stop_network(self):
        """Stop the Hyperledger Fabric network"""
        try:
            os.chdir(self.network_path)
            subprocess.run(["./network.sh", "down"], check=True)
            print("Network stopped successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error stopping network: {e}")
            return False
        
    def deploy_chaincode(self):
        """Deploy the voting chaincode to the network"""
        try:
            os.chdir(self.network_path)
            
            # Package the chaincode
            subprocess.run([
                "peer", "lifecycle", "chaincode", "package", "voting.tar.gz",
                "--path", self.chaincode_path,
                "--lang", "golang",
                "--label", "voting_1.0"
            ], check=True)
            
            # Install the chaincode on Org1
            subprocess.run(["peer", "lifecycle", "chaincode", "install", "voting.tar.gz"], check=True)
            
            # Get the package ID
            result = subprocess.run(
                ["peer", "lifecycle", "chaincode", "queryinstalled"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output to get package ID
            match = re.search(r"Package ID: (.*), Label: voting_1.0", result.stdout)
            if not match:
                print("Failed to find package ID")
                return False
            
            package_id = match.group(1)
            print(f"Package ID: {package_id}")
            
            # Approve for Org1
            orderer_tls_ca = os.path.join(
                self.network_path,
                "organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
            )
            
            subprocess.run([
                "peer", "lifecycle", "chaincode", "approveformyorg",
                "-o", "localhost:7050",
                "--ordererTLSHostnameOverride", "orderer.example.com",
                "--channelID", "votingchannel",
                "--name", "voting",
                "--version", "1.0",
                "--package-id", package_id,
                "--sequence", "1",
                "--tls",
                "--cafile", orderer_tls_ca
            ], check=True)
            
            # Set environment variables for Org2
            self._set_org2_env()
            
            # Install the chaincode on Org2
            subprocess.run(["peer", "lifecycle", "chaincode", "install", "voting.tar.gz"], check=True)
            
            # Approve for Org2
            subprocess.run([
                "peer", "lifecycle", "chaincode", "approveformyorg",
                "-o", "localhost:7050",
                "--ordererTLSHostnameOverride", "orderer.example.com",
                "--channelID", "votingchannel",
                "--name", "voting",
                "--version", "1.0",
                "--package-id", package_id,
                "--sequence", "1",
                "--tls",
                "--cafile", orderer_tls_ca
            ], check=True)
            
            # Reset to Org1 for commit
            self._set_org1_env()
            
            # Commit the chaincode definition
            org1_peer_tls = os.path.join(
                self.network_path,
                "organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
            )
            org2_peer_tls = os.path.join(
                self.network_path,
                "organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt"
            )
            
            subprocess.run([
                "peer", "lifecycle", "chaincode", "commit",
                "-o", "localhost:7050",
                "--ordererTLSHostnameOverride", "orderer.example.com",
                "--channelID", "votingchannel",
                "--name", "voting",
                "--version", "1.0",
                "--sequence", "1",
                "--tls",
                "--cafile", orderer_tls_ca,
                "--peerAddresses", "localhost:7051",
                "--tlsRootCertFiles", org1_peer_tls,
                "--peerAddresses", "localhost:9051",
                "--tlsRootCertFiles", org2_peer_tls
            ], check=True)
            
            print("Chaincode deployed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error deploying chaincode: {e}")
            return False
    
    def invoke_chaincode(self, func_name, args):
        """Invoke a chaincode function"""
        try:
            os.chdir(self.network_path)
            self._set_org1_env()
            
            orderer_tls_ca = os.path.join(
                self.network_path,
                "organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
            )
            
            org1_peer_tls = os.path.join(
                self.network_path,
                "organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
            )
            org2_peer_tls = os.path.join(
                self.network_path,
                "organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt"
            )
            
            # Convert args to proper format
            formatted_args = [str(arg) for arg in args]
            
            subprocess.run([
                "peer", "chaincode", "invoke",
                "-o", "localhost:7050",
                "--ordererTLSHostnameOverride", "orderer.example.com",
                "--tls",
                "--cafile", orderer_tls_ca,
                "-C", "votingchannel",
                "-n", "voting",
                "--peerAddresses", "localhost:7051",
                "--tlsRootCertFiles", org1_peer_tls,
                "--peerAddresses", "localhost:9051",
                "--tlsRootCertFiles", org2_peer_tls,
                "-c", json.dumps({"function": func_name, "Args": formatted_args})
            ], check=True)
            
            print(f"Successfully invoked {func_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error invoking chaincode function {func_name}: {e}")
            return False

    def query_chaincode(self, func_name, args):
        """Query a chaincode function"""
        try:
            os.chdir(self.network_path)
            self._set_org1_env()
            
            formatted_args = [str(arg) for arg in args]
            
            result = subprocess.run([
                "peer", "chaincode", "query",
                "-C", "votingchannel",
                "-n", "voting",
                "-c", json.dumps({"function": func_name, "Args": formatted_args})
            ], capture_output=True, text=True, check=True)
            
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error querying chaincode function {func_name}: {e}")
            return None

    # Voting-specific methods
    def create_election(self, title, description, start_time, end_time):
        """Create a new election"""
        args = [
            title,
            description,
            int(start_time.timestamp()),
            int(end_time.timestamp())
        ]
        return self.invoke_chaincode("CreateElection", args)

    def add_candidate(self, election_id, name):
        """Add a candidate to an election"""
        return self.invoke_chaincode("AddCandidate", [election_id, name])

    def cast_vote(self, election_id, candidate_id, voter_id):
        """Cast a vote in an election"""
        return self.invoke_chaincode("CastVote", [election_id, candidate_id, voter_id])

    def get_election(self, election_id):
        """Get election details"""
        return self.query_chaincode("GetElection", [election_id])

    def get_candidate(self, election_id, candidate_id):
        """Get candidate details"""
        return self.query_chaincode("GetCandidate", [election_id, candidate_id])

    def get_election_results(self, election_id):
        """Get election results"""
        return self.query_chaincode("GetResults", [election_id])

    def get_voter_status(self, election_id, voter_id):
        """Check if a voter has voted"""
        return self.query_chaincode("HasVoted", [election_id, voter_id])