from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """Send welcome email when new user is created"""
    if created:
        subject = 'Welcome to Our Voting Platform'
        message = f'Hi {instance.username},\n\nWelcome to our blockchain voting platform! Your account has been successfully created.'
        try:
            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@votingplatform.com'),
                [instance.email],
                fail_silently=True,  # Changed to True to prevent errors in development
            )
        except Exception as e:
            # Log the error in production
            print(f"Failed to send welcome email to {instance.email}: {e}")