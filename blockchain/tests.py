from django.test import TestCase
from unittest.mock import patch, MagicMock
from blockchain.ethereum_handler import EthereumHandler
from blockchain.hyperledger_handler import HyperledgerHandler
from blockchain.ipfs_handler import IPFSHandler

class TestEthereumHandler(TestCase):
    @patch('web3.Web3')
    def test_create_election_success(self, mock_web3):
        # Setup mock Web3 instance
        mock_instance = MagicMock()
        mock_web3.return_value = mock_instance
        
        # Mock contract interactions
        mock_contract = MagicMock()
        mock_instance.eth.contract.return_value = mock_contract
        mock_contract.functions.createElection.return_value.transact.return_value = 'tx_hash'
        mock_instance.eth.wait_for_transaction_receipt.return_value = {'logs': []}
        
        # Test the handler
        handler = EthereumHandler()
        result = handler.create_election("Test", "Desc", 123, 456)
        self.assertIsNone(result)  # No event emitted in this mock

class TestHyperledgerHandler(TestCase):
    @patch('subprocess.run')
    def test_create_election_success(self, mock_run):
        # Setup mock subprocess response
        mock_result = MagicMock()
        mock_result.stdout = '{"success": true}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Test the handler
        handler = HyperledgerHandler()
        self.assertTrue(handler.create_election("Test", "Desc", 123, 456))

class TestIPFSHandler(TestCase):
    @patch('ipfshttpclient.Client')
    def test_add_json_success(self, mock_ipfs):
        # Setup mock IPFS client
        mock_client = MagicMock()
        mock_client.add_str.return_value = 'QmHash'
        mock_ipfs.return_value = mock_client
        
        # Test the handler
        handler = IPFSHandler()
        self.assertEqual(handler.add_json({"test": "data"}), 'QmHash')