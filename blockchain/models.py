from django.db import models
from django.core.validators import MinLengthValidator

class BlockchainTransaction(models.Model):
    BLOCKCHAIN_CHOICES = [
        ('ETH', 'Ethereum'),
        ('HLF', 'Hyperledger Fabric'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]
    
    tx_hash = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(10)]
    )
    blockchain_type = models.CharField(max_length=3, choices=BLOCKCHAIN_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tx_hash']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.blockchain_type}:{self.tx_hash}"