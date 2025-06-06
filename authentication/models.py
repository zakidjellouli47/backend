# models.py (authentication app)
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_candidate = models.BooleanField(default=False)
    is_elector = models.BooleanField(default=True)
    wallet_address = models.CharField(max_length=42, blank=True, null=True)
    verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def clean(self):
        if self.wallet_address and not self.wallet_address.startswith('0x'):
            raise ValidationError('Wallet address must start with 0x')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)