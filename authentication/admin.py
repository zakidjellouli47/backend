from django.contrib import admin
from .models import Election, Candidate, Vote

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'blockchain', 'start_time', 'end_time', 'is_active')
    list_filter = ('blockchain', 'is_active')

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('user', 'election', 'votes_received')
    search_fields = ('user__email', 'user__username')

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'election', 'candidate', 'is_verified')
    list_filter = ('election', 'is_verified')