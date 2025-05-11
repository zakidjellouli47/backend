from django.contrib import admin
from django.urls import path, include
from authentication.views import (
    register, 
    login, 
    # logout,
    # home
)

urlpatterns = [
    # path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/auth/', include([
        path('register/', register, name='register'),
        path('login/', login, name='login'),
        # path('logout/', logout, name='logout'),
    ])),
    path('api/voting/', include('voting.urls')),
]