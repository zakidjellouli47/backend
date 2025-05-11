from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator

class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name='email address')
    is_candidate = models.BooleanField(default=False)
    is_elector = models.BooleanField(default=False)
    wallet_address = models.CharField(
        max_length=42,
        blank=True,
        null=True,
        validators=[MinLengthValidator(42)]
    )
    public_key = models.TextField(blank=True, null=True)
    verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def clean(self):
        if self.wallet_address and not self.wallet_address.startswith('0x'):
            raise ValidationError('Wallet address must start with 0x')
        if self.is_candidate and self.is_elector:
            raise ValidationError('User cannot be both candidate and elector')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

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
    contract_address = models.CharField(max_length=42, blank=True, null=True)
    election_id = models.CharField(max_length=100, blank=True, null=True)
    ipfs_hash = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_elections'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Election'
        verbose_name_plural = 'Elections'

    @property
    def is_active(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time')

class Candidate(models.Model):
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name='candidates'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='candidacies'
    )
    candidate_id = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True)
    votes_received = models.PositiveIntegerField(default=0)
    approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('election', 'user')
        verbose_name = 'Candidate'
        verbose_name_plural = 'Candidates'

class Vote(models.Model):
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    voter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='votes_received'
    )
    tx_hash = models.CharField(max_length=100, unique=True)
    blockchain = models.CharField(max_length=3)
    voted_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ('election', 'voter')
        verbose_name = 'Vote'
        verbose_name_plural = 'Votes'
        indexes = [
            models.Index(fields=['tx_hash']),
            models.Index(fields=['election', 'voter']),
        ]