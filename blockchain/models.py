from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.utils import timezone
from typing import Dict, Optional

class BlockchainTransaction(models.Model):
    BLOCKCHAIN_CHOICES = [
        ('ETH', 'Ethereum'),
        ('HLF', 'Hyperledger Fabric'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    tx_hash = models.CharField(
        max_length=100,
        unique=True,
        validators=[
            MinLengthValidator(10),
            MaxLengthValidator(100)
        ],
        verbose_name='Transaction Hash',
        help_text='Unique blockchain transaction identifier'
    )
    blockchain_type = models.CharField(
        max_length=3,
        choices=BLOCKCHAIN_CHOICES,
        verbose_name='Blockchain Type'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    details = models.JSONField(
        default=dict,
        verbose_name='Transaction Details'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this transaction will expire if not confirmed'
    )
    confirmations = models.PositiveIntegerField(
        default=0,
        help_text='Number of blockchain confirmations'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Blockchain Transaction'
        verbose_name_plural = 'Blockchain Transactions'
        indexes = [
            models.Index(fields=['tx_hash']),
            models.Index(fields=['status']),
            models.Index(fields=['blockchain_type', 'status']),
            models.Index(fields=['created_at', 'updated_at']),
        ]
    
    def __str__(self):
        return f"{self.blockchain_type}:{self.tx_hash[:10]}...{self.tx_hash[-4:]}"
    
    def is_expired(self) -> bool:
        """Check if the transaction has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def update_status(self, new_status: str, details: Optional[Dict] = None) -> None:
        """
        Update transaction status with validation
        
        Args:
            new_status: One of STATUS_CHOICES values
            details: Optional additional details to merge
        """
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValueError(f"Invalid status: {new_status}")
            
        self.status = new_status
        if details:
            self.details.update(details)
            
        if new_status == 'confirmed':
            self.confirmations += 1
            
        self.save()
    
    def get_short_hash(self) -> str:
        """Get shortened version of transaction hash"""
        return f"{self.tx_hash[:6]}...{self.tx_hash[-4:]}"
    
    def refresh_from_blockchain(self) -> bool:
        """
        Attempt to refresh transaction status from blockchain
        
        Returns:
            bool: True if status was updated, False otherwise
        """
        try:
            if self.blockchain_type == 'ETH':
                from .ethereum_handler import EthereumHandler
                handler = EthereumHandler()
                status = handler.get_transaction_status(self.tx_hash)
            else:
                from .hyperledger_handler import HyperledgerHandler
                handler = HyperledgerHandler()
                status = handler.get_transaction_status(self.tx_hash)
            
            if status and status != self.status:
                self.update_status(status)
                return True
            return False
        except Exception as e:
            if 'refresh_error' not in self.details:
                self.details['refresh_error'] = []
            self.details['refresh_error'].append({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            })
            self.save()
            return False