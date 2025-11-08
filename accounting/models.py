from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    # Django user
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client_profile',
        null=True, blank=True
    )

    full_name = models.CharField(max_length=200)


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


class Worker(models.Model):
    # using Django user to enter into admin panel
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='worker_profile'
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"


class Transaction(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,  # avoid deleting client if there is a transaction
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

    receipt_printed = models.BooleanField(default=False)

    def __str__(self):
        return f"Сеанс {self.client.full_name} с {self.worker.user.username} на {self.amount}"

    class Meta:
        verbose_name = "Транзакция/Сеанс"
        verbose_name_plural = "Транзакции/Сеансы"
        ordering = ['-date_time']


class ClientDeposit(models.Model):
        client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='deposits')
        amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма пополнения")
        date_time = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")

        def __str__(self):
            return f"Пополнение {self.client.full_name} на {self.amount}"

        class Meta:
            verbose_name = "Пополнение клиента"
            verbose_name_plural = "Пополнения клиентов"
            ordering = ['-date_time']
