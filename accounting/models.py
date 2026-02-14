from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    CLIENT_TYPE_CHOICES = [
        ('child', 'Ребенок'),
        ('teenager', 'Подросток'),
        ('adult', 'Взрослый'),
    ]

    # Django user
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client_profile',
        null=True, blank=True
    )

    full_name = models.CharField(max_length=200, verbose_name="ФИО")
    
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Дата рождения")
    
    address = models.TextField(blank=True, verbose_name="Адрес")
    
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    
    referral_source = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name="Откуда узнал о центре"
    )
    
    client_type = models.CharField(
        max_length=20,
        choices=CLIENT_TYPE_CHOICES,
        default='adult',
        verbose_name="Тип клиента"
    )

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    # Count of prepaid lessons for the client
    lessons_balance = models.PositiveIntegerField(
        default=0,
        verbose_name="Lessons balance"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name="Дата обновления")

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

    # Number of lessons included in this payment
    lessons_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Lessons count"
    )

    # Snapshot of balances right after the transaction
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Balance after"
    )
    lessons_balance_after = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Lessons balance after"
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

    # How many lessons were added with this deposit
    lessons_added = models.PositiveIntegerField(
        default=0,
        verbose_name="Lessons added"
    )

    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Balance after"
    )
    lessons_balance_after = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Lessons balance after"
    )

    def __str__(self):
        return f"Пополнение {self.client.full_name} на {self.amount}"

    class Meta:
        verbose_name = "Пополнение клиента"
        verbose_name_plural = "Пополнения клиентов"
        ordering = ['-date_time']
