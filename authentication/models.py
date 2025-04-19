from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_candidate = models.BooleanField(default=False)
    is_elector = models.BooleanField(default=False)
    wallet_address = models.CharField(max_length=42, blank=True, null=True)
    public_key = models.TextField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

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
    eth_contract_address = models.CharField(max_length=42, blank=True, null=True)
    eth_election_id = models.PositiveIntegerField(blank=True, null=True)
    hlf_election_id = models.CharField(max_length=100, blank=True, null=True)
    ipfs_hash = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_active(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time

class Candidate(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    eth_candidate_id = models.PositiveIntegerField(blank=True, null=True)
    hlf_candidate_id = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True)
    votes_received = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('election', 'user')

class Vote(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    voter = models.ForeignKey(User, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    tx_hash = models.CharField(max_length=100)
    blockchain = models.CharField(max_length=3)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('election', 'voter')