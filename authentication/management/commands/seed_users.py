from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with test users'

    def handle(self, *args, **options):
        self.stdout.write("Seeding user data...")
        
        # Create test candidates
        candidates = [
            {'email': 'candidate1@example.com', 'username': 'candidate1', 'password': 'testpass123', 'is_candidate': True},
            {'email': 'candidate2@example.com', 'username': 'candidate2', 'password': 'testpass123', 'is_candidate': True},
        ]
        
        # Create test electors
        electors = [
            {'email': 'elector1@example.com', 'username': 'elector1', 'password': 'testpass123', 'is_elector': True},
            {'email': 'elector2@example.com', 'username': 'elector2', 'password': 'testpass123', 'is_elector': True},
        ]
        
        # Create admin user
        admin_user = {
            'email': 'admin@example.com',
            'username': 'admin',
            'password': 'adminpass123',
            'is_staff': True,
            'is_superuser': True
        }
        
        # Create users function
        def create_users(users):
            created = 0
            for user_data in users:
                email = user_data['email']
                if not User.objects.filter(email=email).exists():
                    user = User.objects.create_user(
                        username=user_data['username'],
                        email=email,
                        password=user_data['password']
                    )
                    for attr, value in user_data.items():
                        if attr not in ['username', 'email', 'password']:
                            setattr(user, attr, value)
                    user.save()
                    Token.objects.create(user=user)
                    created += 1
                    self.stdout.write(f"Created user: {email}")
                else:
                    self.stdout.write(f"User already exists: {email}")
            return created
        
        # Create all users
        total_candidates = create_users(candidates)
        total_electors = create_users(electors)
        total_admins = create_users([admin_user])
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully seeded database:\n"
                f"- {total_candidates} candidates created\n"
                f"- {total_electors} electors created\n"
                f"- {total_admins} admin created"
            )
        )