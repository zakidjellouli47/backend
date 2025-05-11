from django.urls import path
from rest_framework.schemas import get_schema_view
from . import views

app_name = 'authentication'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('elections/create/', views.create_election, name='create_election'),
    path('elections/<int:election_id>/register/', views.register_candidate, name='register_candidate'),
    path('elections/<int:election_id>/vote/<int:candidate_id>/', views.cast_vote, name='cast_vote'),
    path('elections/<int:election_id>/results/', views.election_results, name='election_results'),
    
    # API Documentation
    path('schema/', get_schema_view(
        title="Election API",
        description="API for blockchain-based voting system",
        version="1.0.0"
    ), name='openapi-schema'),
]