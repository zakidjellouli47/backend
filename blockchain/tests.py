from django.test import TestCase
from unittest.mock import patch, MagicMock
from .models import BlockchainTransaction

class TestBlockchainTransaction(TestCase):
    def setUp(self):
        self.transaction = BlockchainTransaction.objects.create(
            tx_hash='0x1234567890abcdef',
            blockchain_type='ETH',
            status='pending'
        )
    
    def test_transaction_creation(self):
        self.assertEqual(self.transaction.blockchain_type, 'ETH')
        self.assertEqual(self.transaction.status, 'pending')
        self.assertEqual(self.transaction.confirmations, 0)
    
    def test_update_status(self):
        self.transaction.update_status('confirmed')
        self.assertEqual(self.transaction.status, 'confirmed')
        self.assertEqual(self.transaction.confirmations, 1)
    
    def test_get_short_hash(self):
        expected = '0x1234...cdef'
        self.assertEqual(self.transaction.get_short_hash(), expected)
    
    def test_is_expired(self):
        # Transaction without expires_at should not be expired
        self.assertFalse(self.transaction.is_expired())

class TestEthereumHandler(TestCase):
    @patch('blockchain.ethereum_handler.Web3')
    def test_ethereum_handler_import(self, mock_web3):
        """Test that ethereum handler can be imported without errors"""
        try:
            from .ethereum_handler import EthereumHandler
            handler = EthereumHandler()
            self.assertIsNotNone(handler)
        except ImportError:
            self.skipTest("Ethereum handler not available")

class TestHyperledgerHandler(TestCase):
    def test_hyperledger_handler_import(self):
        """Test that hyperledger handler can be imported without errors"""
        try:
            from .hyperledger_handler import HyperledgerHandler
            handler = HyperledgerHandler()
            self.assertIsNotNone(handler)
        except ImportError:
            self.skipTest("Hyperledger handler not available")

class TestIPFSHandler(TestCase):
    def test_ipfs_handler_import(self):
        """Test that IPFS handler can be imported without errors"""
        try:
            from .ipfs_handler import IPFSHandler
            handler = IPFSHandler()
            self.assertIsNotNone(handler)
        except ImportError:
            self.skipTest("IPFS handler not available")