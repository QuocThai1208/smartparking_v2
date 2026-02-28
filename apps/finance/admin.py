from django.contrib import admin
from .models import Wallet, Payment, WalletTransaction

from ..parking.admin_site import custom_admin_site

class PaymentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'amount', 'status')
    search_fields = ('id', 'user__full_name')
    list_filter   = ('status',)
    autocomplete_fields = ('user',)

class WalletAdmin(admin.ModelAdmin):
    ist_display = ('user', 'balance', 'active')
    search_fields = ('user__username',)


class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'created_date', 'description')
    list_filter = ('transaction_type', 'created_date')
    search_fields = ('wallet__user__username', 'description')


custom_admin_site.register(Payment, PaymentAdmin)
custom_admin_site.register(Wallet, WalletAdmin)
custom_admin_site.register(WalletTransaction, WalletTransactionAdmin)