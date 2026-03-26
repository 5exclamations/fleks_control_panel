from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0010_clientbalanceadjustment"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="default_session_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Шаблонная сумма сеанса"),
        ),
    ]
