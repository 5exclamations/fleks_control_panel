from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0007_add_lessons_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='balance_after',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Balance after'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='lessons_balance_after',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Lessons balance after'),
        ),
        migrations.AddField(
            model_name='clientdeposit',
            name='balance_after',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Balance after'),
        ),
        migrations.AddField(
            model_name='clientdeposit',
            name='lessons_balance_after',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Lessons balance after'),
        ),
    ]
