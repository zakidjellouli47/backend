from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Election, Candidate, Vote

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'is_candidate', 'is_elector', 'verified')
    list_filter = ('is_candidate', 'is_elector', 'verified')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'wallet_address', 'public_key')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 
                      'is_candidate', 'is_elector', 'verified'),
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

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'blockchain', 'start_time', 'end_time', 'is_active', 'is_approved')
    list_filter = ('blockchain', 'is_approved')
    search_fields = ('title', 'description')
    actions = ['approve_elections']

    def approve_elections(self, request, queryset):
        queryset.update(is_approved=True)
    approve_elections.short_description = "Approve selected elections"

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('user', 'election', 'votes_received', 'approved')
    list_filter = ('election', 'approved')
    search_fields = ('user__email', 'user__username')
    actions = ['approve_candidates']

    def approve_candidates(self, request, queryset):
        queryset.update(approved=True)
    approve_candidates.short_description = "Approve selected candidates"

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('election', 'voter', 'candidate', 'voted_at', 'verified')
    list_filter = ('election', 'verified')
    search_fields = ('voter__email', 'tx_hash')
    actions = ['verify_votes']

    def verify_votes(self, request, queryset):
        queryset.update(verified=True)
    verify_votes.short_description = "Verify selected votes"

admin.site.register(User, CustomUserAdmin)