# Generated manually for message requests

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0008_message_is_system'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='is_message_request',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='conversation',
            name='message_request_for',
            field=models.ForeignKey(
                blank=True,
                help_text='User cần chấp nhận tin nhắn chờ này',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pending_message_requests',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
