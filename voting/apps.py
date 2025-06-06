from django.apps import AppConfig

class VotingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'voting'
    
    def ready(self):
        """Import signals when app is ready"""
        import voting.signals
