from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post, Media, Comment, Like, SavedPost, Hashtag, Mention, CommentLike

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar', 'is_verified']

class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ['id', 'file', 'media_type', 'order']

class CommentSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)
    replies_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'text', 'parent',
            'replies_count', 'likes_count', 'is_liked',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['author']
    
    def get_replies_count(self, obj):
        return obj.replies.count()
    
    def get_likes_count(self, obj):
        return obj.comment_likes.count()
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CommentLike.objects.filter(
                user=request.user,
                comment=obj
            ).exists()
        return False

class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ['id', 'name', 'slug', 'posts_count']

class PostSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)
    media = MediaSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'author', 'caption', 'location',
            'media', 'comments', 'hashtags',
            'comments_count', 'likes_count',
            'is_liked', 'is_saved',
            'disable_comments', 'hide_likes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'author', 'comments_count', 'likes_count'
        ]
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                user=request.user,
                post=obj
            ).exists()
        return False
    
    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedPost.objects.filter(
                user=request.user,
                post=obj
            ).exists()
        return False
    
    def create(self, validated_data):
        media_files = self.context['request'].FILES.getlist('media')
        hashtags_data = self.context['request'].data.getlist('hashtags', [])
        mentions_data = self.context['request'].data.getlist('mentions', [])
        
        post = Post.objects.create(
            author=self.context['request'].user,
            **validated_data
        )
        
        # Create media objects
        for index, file in enumerate(media_files):
            media_type = 'video' if file.content_type.startswith('video') else 'image'
            Media.objects.create(
                post=post,
                file=file,
                media_type=media_type,
                order=index
            )
        
        # Process hashtags
        for tag_name in hashtags_data:
            tag_name = tag_name.strip('#')
            hashtag, _ = Hashtag.objects.get_or_create(name=tag_name)
            hashtag.posts.add(post)
            hashtag.posts_count = hashtag.posts.count()
            hashtag.save()
        
        # Process mentions
        for username in mentions_data:
            username = username.strip('@')
            try:
                mentioned_user = User.objects.get(username=username)
                Mention.objects.create(
                    user=mentioned_user,
                    post=post
                )
            except User.DoesNotExist:
                pass
        
        return post 