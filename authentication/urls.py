from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register),
    path('login/', views.login),
    path('elections/create/', views.create_election),
    path('elections/<int:election_id>/register/', views.register_candidate),
    path('elections/<int:election_id>/vote/<int:candidate_id>/', views.cast_vote),
    path('elections/<int:election_id>/results/', views.election_results),
]