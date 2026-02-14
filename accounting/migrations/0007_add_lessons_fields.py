from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0006_add_client_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='lessons_balance',
            field=models.PositiveIntegerField(default=0, verbose_name='Lessons balance'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='lessons_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Lessons count'),
        ),
        migrations.AddField(
            model_name='clientdeposit',
            name='lessons_added',
            field=models.PositiveIntegerField(default=0, verbose_name='Lessons added'),
        ),
    ]
