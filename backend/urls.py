from django.contrib import admin
from django.urls import path
from authentication.views import (
    register, 
    login, 
    verify_auth, 
    logout,
    home  # We'll add this new view
)

urlpatterns = [
    path('', home, name='home'),  # Root URL
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('verify-auth/', verify_auth, name='verify-auth'),
    path('logout/', logout, name='logout'),
]