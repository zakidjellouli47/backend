from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'is_candidate', 'is_elector', 'verified')
    list_filter = ('is_candidate', 'is_elector', 'verified')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'wallet_address')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_candidate', 'is_elector', 'verified'),
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'username')
    ordering = ('email',)

admin.site.register(User, CustomUserAdmin)