# voting/urls.py
from django.urls import path
from . import views

app_name = 'voting'

urlpatterns = [
    # Election management
    path('elections/', views.get_elections, name='get_elections'),
    path('elections/create/', views.create_election, name='create_election'),
    path('elections/<str:election_id>/', views.get_election_details, name='election_details'),
    path('elections/<str:election_id>/results/', views.get_election_results, name='election_results'),
    
    # Candidate management
    path('elections/<str:election_id>/candidates/add/', views.add_candidate, name='add_candidate'),
    
    # Voting
    path('elections/<str:election_id>/vote/', views.cast_vote, name='cast_vote'),
    path('elections/<str:election_id>/vote-status/', views.check_vote_status, name='check_vote_status'),
    
    # Transaction tracking
    path('transactions/<str:tx_hash>/', views.get_transaction_status, name='transaction_status'),
]