# tests.py (authentication app)
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import User

class UserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.is_elector)  # Default should be True
        self.assertFalse(user.is_candidate)  # Default should be False
        self.assertFalse(user.verified)  # Default should be False

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='adminpass'
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertEqual(admin.email, 'admin@example.com')

    def test_user_str_method(self):
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.assertEqual(str(user), 'test@example.com')

class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.registration_url = reverse('authentication:register')
        self.login_url = reverse('authentication:login')
        self.logout_url = reverse('authentication:logout')
        self.verify_url = reverse('authentication:verify_auth')
        
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'role': 'elector'
        }

    def test_user_registration_elector(self):
        """Test user registration as elector"""
        response = self.client.post(self.registration_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('token' in response.data)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertTrue(response.data['is_elector'])
        self.assertFalse(response.data['is_candidate'])

    def test_user_registration_candidate(self):
        """Test user registration as candidate"""
        candidate_data = self.user_data.copy()
        candidate_data['role'] = 'candidate'
        candidate_data['email'] = 'candidate@example.com'
        
        response = self.client.post(self.registration_url, candidate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('token' in response.data)
        self.assertEqual(response.data['email'], 'candidate@example.com')
        self.assertFalse(response.data['is_elector'])
        self.assertTrue(response.data['is_candidate'])

    def test_user_registration_invalid_role(self):
        """Test user registration with invalid role"""
        invalid_data = self.user_data.copy()
        invalid_data['role'] = 'invalid_role'
        
        response = self.client.post(self.registration_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_duplicate_email(self):
        """Test user registration with duplicate email"""
        # Create first user
        self.client.post(self.registration_url, self.user_data, format='json')
        
        # Try to create second user with same email
        duplicate_data = self.user_data.copy()
        duplicate_data['username'] = 'differentuser'
        
        response = self.client.post(self.registration_url, duplicate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_valid(self):
        """Test user login with valid credentials"""
        # Register user first
        self.client.post(self.registration_url, self.user_data, format='json')
        
        # Login
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('token' in response.data)
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials"""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_missing_fields(self):
        """Test user login with missing fields"""
        login_data = {
            'email': 'test@example.com'
            # Missing password
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_logout(self):
        """Test user logout"""
        # Register and login first
        register_response = self.client.post(self.registration_url, self.user_data, format='json')
        token = register_response.data['token']
        
        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        
        # Logout
        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Successfully logged out')

    def test_verify_auth_authenticated(self):
        """Test auth verification with authenticated user"""
        # Register user
        register_response = self.client.post(self.registration_url, self.user_data, format='json')
        token = register_response.data['token']
        
        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        
        # Verify auth
        response = self.client.get(self.verify_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertTrue(response.data['is_elector'])

    def test_verify_auth_unauthenticated(self):
        """Test auth verification without authentication"""
        response = self.client.get(self.verify_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_connect_wallet_authenticated(self):
        """Test wallet connection with authenticated user"""
        # Register user
        register_response = self.client.post(self.registration_url, self.user_data, format='json')
        token = register_response.data['token']
        
        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        
        # Connect wallet
        wallet_data = {'wallet_address': '0x1234567890abcdef'}
        response = self.client.post(reverse('authentication:connect_wallet'), wallet_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['wallet_address'], '0x1234567890abcdef')

    def test_connect_wallet_unauthenticated(self):
        """Test wallet connection without authentication"""
        wallet_data = {'wallet_address': '0x1234567890abcdef'}
        response = self.client.post(reverse('authentication:connect_wallet'), wallet_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)