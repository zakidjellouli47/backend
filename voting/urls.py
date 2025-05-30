from django.urls import path
from . import views

app_name = 'voting'

urlpatterns = [
    # Election Management
    path('elections/', views.create_election, name='create_election'),
    
    path('elections/<int:election_id>/vote/', views.cast_vote, name='cast_vote'),
    path('elections/<int:election_id>/results/', views.election_results, name='election_results'),
    path('elections/<int:election_id>/candidates/', views.list_candidates, name='list_candidates'),
    path('elections/<int:election_id>/register/', views.register_candidate, name='register_candidate'),
    # Blockchain Verification
    path('verify/vote/<str:tx_hash>/', views.verify_vote, name='verify_vote'),
]