from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0001_initial'),
        ('chat', '0003_usersetting_last_seen'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversationmessage',
            name='shared_post',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='shared_in_messages',
                to='posts.post',
            ),
        ),
    ]
