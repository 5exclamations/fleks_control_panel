# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0005_remove_worker_balance_delete_workerpayout'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True, verbose_name='Дата рождения'),
        ),
        migrations.AddField(
            model_name='client',
            name='address',
            field=models.TextField(blank=True, verbose_name='Адрес'),
        ),
        migrations.AddField(
            model_name='client',
            name='phone',
            field=models.CharField(blank=True, max_length=20, verbose_name='Телефон'),
        ),
        migrations.AddField(
            model_name='client',
            name='referral_source',
            field=models.CharField(blank=True, max_length=200, verbose_name='Откуда узнал о центре'),
        ),
        migrations.AddField(
            model_name='client',
            name='client_type',
            field=models.CharField(choices=[('child', 'Ребенок'), ('teenager', 'Подросток'), ('adult', 'Взрослый')], default='adult', max_length=20, verbose_name='Тип клиента'),
        ),
        migrations.AddField(
            model_name='client',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='client',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='Дата обновления'),
        ),
    ]

