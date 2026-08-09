# Generated manually for audio media on posts

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0003_comment_video'),
    ]

    operations = [
        migrations.AlterField(
            model_name='media',
            name='media_type',
            field=models.CharField(
                choices=[('image', 'Image'), ('video', 'Video'), ('audio', 'Audio')],
                default='image',
                max_length=5,
            ),
        ),
        migrations.AlterField(
            model_name='postmedia',
            name='media_type',
            field=models.CharField(
                choices=[('image', 'Image'), ('video', 'Video'), ('audio', 'Audio')],
                default='image',
                max_length=5,
                verbose_name='media type',
            ),
        ),
    ]
