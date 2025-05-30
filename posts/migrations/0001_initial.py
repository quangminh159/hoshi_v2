# Generated by Django 5.0.4 on 2025-05-19 16:26

import django.db.models.deletion
import imagekit.models.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('likes_count', models.PositiveIntegerField(default=0)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to=settings.AUTH_USER_MODEL)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='posts.comment')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('caption', models.TextField(blank=True)),
                ('location', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('likes_count', models.PositiveIntegerField(default=0)),
                ('comments_count', models.PositiveIntegerField(default=0)),
                ('disable_comments', models.BooleanField(default=False)),
                ('hide_likes', models.BooleanField(default=False)),
                ('is_archived', models.BooleanField(default=False)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to=settings.AUTH_USER_MODEL)),
                ('shared_from', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shared_posts', to='posts.post')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Mention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to='posts.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to='posts.post')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='posts/', verbose_name='file')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], default='image', max_length=5)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_media', to='posts.post')),
            ],
            options={
                'verbose_name': 'media',
                'verbose_name_plural': 'media',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='Like',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_likes', to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_likes', to='posts.post')),
            ],
            options={
                'verbose_name': 'like',
                'verbose_name_plural': 'likes',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Hashtag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('posts_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('posts', models.ManyToManyField(related_name='hashtags', to='posts.post')),
            ],
        ),
        migrations.AddField(
            model_name='comment',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='posts.post'),
        ),
        migrations.CreateModel(
            name='PostMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='posts', verbose_name='file')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], default='image', max_length=5, verbose_name='media type')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to='posts.post')),
            ],
            options={
                'verbose_name': 'post media',
                'verbose_name_plural': 'post media',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='PostReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('spam', 'Spam'), ('inappropriate', 'Inappropriate content'), ('violence', 'Violence'), ('hate_speech', 'Hate speech'), ('other', 'Other')], max_length=20, verbose_name='reason')),
                ('details', models.TextField(blank=True, verbose_name='details')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_resolved', models.BooleanField(default=False, verbose_name='resolved')),
                ('is_valid', models.BooleanField(blank=True, null=True, verbose_name='valid report')),
                ('resolved_at', models.DateTimeField(blank=True, null=True, verbose_name='resolved at')),
                ('admin_notes', models.TextField(blank=True, null=True, verbose_name='admin notes')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='posts.post')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_post_reports', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'post report',
                'verbose_name_plural': 'post reports',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SavedPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by', to='posts.post')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_posts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media', imagekit.models.fields.ProcessedImageField(upload_to='stories')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], default='image', max_length=5, verbose_name='media type')),
                ('caption', models.TextField(blank=True, max_length=2200, verbose_name='caption')),
                ('location', models.CharField(blank=True, max_length=100, verbose_name='location')),
                ('is_highlight', models.BooleanField(default=False, verbose_name='highlight')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'story',
                'verbose_name_plural': 'stories',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StoryView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('story', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='views', to='posts.story')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='story_views', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'story view',
                'verbose_name_plural': 'story views',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='story',
            name='viewers',
            field=models.ManyToManyField(related_name='viewed_stories', through='posts.StoryView', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='UserInteraction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interaction_type', models.CharField(choices=[('view', 'Xem'), ('like', 'Thích'), ('comment', 'Bình luận'), ('share', 'Chia sẻ'), ('save', 'Lưu'), ('click', 'Click vào chi tiết')], max_length=20)),
                ('duration', models.PositiveIntegerField(default=0, help_text='Thời gian tương tác tính bằng giây')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_interactions', to='posts.post')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tương tác người dùng',
                'verbose_name_plural': 'Tương tác người dùng',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CommentLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comment_likes', to='posts.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comment_likes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'comment like',
                'verbose_name_plural': 'comment likes',
                'ordering': ['-created_at'],
                'unique_together': {('user', 'comment')},
            },
        ),
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['-created_at'], name='posts_post_created_183a3b_idx'),
        ),
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['author', '-created_at'], name='posts_post_author__f8ea20_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='like',
            unique_together={('user', 'post')},
        ),
        migrations.AlterUniqueTogether(
            name='postreport',
            unique_together={('user', 'post')},
        ),
        migrations.AlterUniqueTogether(
            name='savedpost',
            unique_together={('user', 'post')},
        ),
        migrations.AlterUniqueTogether(
            name='storyview',
            unique_together={('user', 'story')},
        ),
        migrations.AddIndex(
            model_name='userinteraction',
            index=models.Index(fields=['user', 'interaction_type'], name='posts_useri_user_id_e0ea22_idx'),
        ),
        migrations.AddIndex(
            model_name='userinteraction',
            index=models.Index(fields=['post', 'interaction_type'], name='posts_useri_post_id_80f76e_idx'),
        ),
    ]
