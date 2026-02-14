from django.contrib import admin
from .models import Client, Worker, Transaction, ClientDeposit, ClientBalanceAdjustment


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'client', 'worker', 'amount', 'lessons_count', 'receipt_printed')

    list_filter = ('worker', 'date_time', 'receipt_printed')

    search_fields = ('client__full_name', 'worker__user__username')

    readonly_fields = ('date_time', 'client', 'worker', 'amount', 'lessons_count')

#admin panel for clients
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'balance', 'lessons_balance')
    search_fields = ('full_name',)


# admin panel for workers
@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('get_username',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


    def get_username(self, obj):
        return obj.user.username

    get_username.short_description = 'Пользователь (Логин)'
@admin.register(ClientDeposit)
class ClientDepositAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'client', 'amount', 'lessons_added')
    list_filter = ('date_time',)
    search_fields = ('client__full_name',)


@admin.register(ClientBalanceAdjustment)
class ClientBalanceAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'client', 'amount_removed', 'lessons_removed')
    list_filter = ('date_time',)
    search_fields = ('client__full_name',)
