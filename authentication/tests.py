from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import User, Election, Candidate

class UserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertFalse(user.is_candidate)
        self.assertFalse(user.is_elector)

class ElectionAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='adminpass'
        )
        self.elector = User.objects.create_user(
            email='elector@example.com',
            username='elector',
            password='electorpass',
            is_elector=True
        )
        self.candidate = User.objects.create_user(
            email='candidate@example.com',
            username='candidate',
            password='candidatepass',
            is_candidate=True
        )
        
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(days=1)
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            start_time=start_time,
            end_time=end_time,
            blockchain='ETH',
            created_by=self.elector
        )

    def test_create_election(self):
        self.client.force_authenticate(user=self.elector)
        url = reverse('authentication:create_election')
        data = {
            'title': 'New Election',
            'description': 'New Description',
            'start_time': (timezone.now() + timedelta(days=2)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=3)).isoformat(),
            'blockchain': 'ETH'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Election.objects.count(), 2)

    def test_register_candidate(self):
        self.client.force_authenticate(user=self.candidate)
        url = reverse('authentication:register_candidate', args=[self.election.id])
        data = {'bio': 'Test bio'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Candidate.objects.filter(
            election=self.election,
            user=self.candidate
        ).exists())

    def test_vote(self):
        candidate = Candidate.objects.create(
            election=self.election,
            user=self.candidate,
            approved=True
        )
        self.client.force_authenticate(user=self.elector)
        url = reverse('authentication:cast_vote', args=[self.election.id, candidate.id])
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(candidate.votes_received, 1)