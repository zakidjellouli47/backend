from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Vote

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        subject = 'Welcome to Our Voting Platform'
        message = f'Hi {instance.username},\n\nWelcome to our platform!'
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=False,
        )

@receiver(post_save, sender=Vote)
def notify_vote_cast(sender, instance, created, **kwargs):
    if created:
        subject = 'Your vote has been cast'
        message = f'You have successfully voted in {instance.election.title}'
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.voter.email],
            fail_silently=False,
        )