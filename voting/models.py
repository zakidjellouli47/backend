from django.db import models
from django.core.validators import MinLengthValidator
from authentication.models import User

class Election(models.Model):
    BLOCKCHAIN_CHOICES = [
        ('ETH', 'Ethereum'),
        ('HLF', 'Hyperledger Fabric'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    blockchain = models.CharField(max_length=3, choices=BLOCKCHAIN_CHOICES)
    contract_address = models.CharField(max_length=42, blank=True, null=True, 
                                      validators=[MinLengthValidator(42)])
    election_id = models.CharField(max_length=100)  # Universal ID for both blockchains
    ipfs_hash = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['blockchain', 'election_id']),
        ]

    @property
    def is_active(self):
        from django.utils import timezone
        now = timezone.now()
        return self.start_time <= now <= self.end_time

class Candidate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='candidacies')
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    candidate_id = models.CharField(max_length=100)  # Universal ID
    bio = models.TextField(blank=True)
    votes_received = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('election', 'user')
        ordering = ['-votes_received']

class Vote(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes')
    tx_hash = models.CharField(max_length=100, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ('election', 'voter')
        indexes = [
            models.Index(fields=['tx_hash']),
            models.Index(fields=['election', 'voter']),
        ]