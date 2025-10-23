# accounting/models.py

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


# Модель клиента
class Client(models.Model):
    # Привязка к встроенному пользователю Django (если нужна аутентификация)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client_profile',
        null=True, blank=True
    )
    # Или просто имя/контакт, если отдельная аутентификация не нужна
    full_name = models.CharField(max_length=200)

    # Главное поле: баланс клиента
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"


# Модель сотрудника (психолога)
class Worker(models.Model):
    # Используем встроенного пользователя Django для входа в систему и админки
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='worker_profile'
    )

    # Баланс сотрудника (его доход)
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"


# Модель транзакции (сеанса)
class Transaction(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,  # Не удалять клиента, если у него есть транзакции
        related_name='transactions_as_client'
    )
    worker = models.ForeignKey(
        Worker,
        on_delete=models.PROTECT,
        related_name='transactions_as_worker'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Стоимость сеанса"
    )

    date_time = models.DateTimeField(auto_now_add=True)

    # Флаг для печати чека (для отслеживания, был ли чек распечатан)
    receipt_printed = models.BooleanField(default=False)

    def __str__(self):
        return f"Сеанс {self.client.full_name} с {self.worker.user.username} на {self.amount}"

    class Meta:
        verbose_name = "Транзакция/Сеанс"
        verbose_name_plural = "Транзакции/Сеансы"
        ordering = ['-date_time']  # Новые транзакции сверху

    # accounting/models.py
    # ... (в конце файла, после класса Transaction) ...

class ClientDeposit(models.Model):
        """Модель для отслеживания пополнений баланса клиентами."""
        client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='deposits')
        amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма пополнения")
        date_time = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")

        def __str__(self):
            return f"Пополнение {self.client.full_name} на {self.amount}"

        class Meta:
            verbose_name = "Пополнение клиента"
            verbose_name_plural = "Пополнения клиентов"
            ordering = ['-date_time']  # Новые сверху

class WorkerPayout(models.Model):
        """Модель для отслеживания выплат сотрудникам."""
        worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='payouts')
        amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма выплаты")
        date_time = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")

        def __str__(self):
            return f"Выплата {self.worker.user.username} на {self.amount}"

        class Meta:
            verbose_name = "Выплата сотруднику"
            verbose_name_plural = "Выплаты сотрудникам"
            ordering = ['-date_time']  # Новые сверху