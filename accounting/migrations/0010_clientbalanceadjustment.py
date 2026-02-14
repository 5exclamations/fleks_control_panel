from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0009_alter_client_full_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientBalanceAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount_removed", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Списанная сумма")),
                ("lessons_removed", models.PositiveIntegerField(default=0, verbose_name="Списанные уроки")),
                ("date_time", models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")),
                ("balance_after", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Balance after")),
                ("lessons_balance_after", models.PositiveIntegerField(blank=True, null=True, verbose_name="Lessons balance after")),
                (
                    "client",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="balance_adjustments", to="accounting.client"),
                ),
            ],
            options={
                "verbose_name": "Отмена пополнения",
                "verbose_name_plural": "Отмены пополнений",
                "ordering": ["-date_time"],
            },
        ),
    ]
