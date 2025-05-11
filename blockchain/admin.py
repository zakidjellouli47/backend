from django.contrib import admin
from blockchain.models import BlockchainTransaction

@admin.register(BlockchainTransaction)
class BlockchainTransactionAdmin(admin.ModelAdmin):
    list_display = ('tx_hash', 'blockchain_type', 'status', 'created_at')
    list_filter = ('blockchain_type', 'status')
    search_fields = ('tx_hash',)
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['retry_failed_transactions']

    def retry_failed_transactions(self, request, queryset):
        # For now, just update status to pending
        updated = queryset.filter(status='failed').update(status='pending')
        self.message_user(
            request, 
            f"Marked {updated} failed transactions for retry. "
            "Note: Actual retry requires Celery worker to be running."
        )