# Generated manually for comment audio

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0004_postmedia_audio'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='audio',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='comments/audio/%Y/%m/',
                verbose_name='audio',
            ),
        ),
    ]
