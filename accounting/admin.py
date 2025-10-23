from django.contrib import admin

# Register your models here.
# accounting/admin.py

from django.contrib import admin
# Добавьте ClientDeposit и WorkerPayout
from .models import Client, Worker, Transaction, ClientDeposit, WorkerPayout


# 1. Административная панель для Транзакций
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    # Поля, которые будут отображаться в списке транзакций
    list_display = ('date_time', 'client', 'worker', 'amount', 'receipt_printed')
    # Поля, по которым можно фильтровать
    list_filter = ('worker', 'date_time', 'receipt_printed')
    # Поля, по которым можно искать
    search_fields = ('client__full_name', 'worker__user__username')
    # Поля, которые нельзя редактировать после создания
    readonly_fields = ('date_time', 'client', 'worker', 'amount')

    # Добавление возможности просмотра чека прямо из списка (если нужна)
    # actions = ['print_receipt_action']

    # def print_receipt_action(self, request, queryset):
    #     # Здесь можно вызвать вашу функцию print_receipt_for_session
    #     # print_receipt_for_session(queryset.first())
    #     pass
    # print_receipt_action.short_description = "Распечатать чек для выбранной транзакции"


# 2. Административная панель для Клиентов
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'balance')
    search_fields = ('full_name',)


# 3. Административная панель для Сотрудников
@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'balance')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

    # Метод для отображения имени пользователя из связанной модели User
    def get_username(self, obj):
        return obj.user.username

    get_username.short_description = 'Пользователь (Логин)'
@admin.register(ClientDeposit)
class ClientDepositAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'client', 'amount')
    list_filter = ('date_time',)
    search_fields = ('client__full_name',)

@admin.register(WorkerPayout)
class WorkerPayoutAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'worker', 'amount')
    list_filter = ('date_time',)
    search_fields = ('worker__user__username',)