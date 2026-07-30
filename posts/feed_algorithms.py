from django.db.models import Q, Case, When
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import random


def _following_ids(user):
  return user.get_following_user_ids()


def _blocked_author_ids(user):
    return user.get_blocked_user_ids()


def _base_feed_queryset(user):
    """Queryset chung cho feed — lọc block, private account."""
    from posts.models import Post

    following_ids = _following_ids(user)
    blocked_ids = _blocked_author_ids(user)

    return Post.objects.filter(
        is_archived=False,
        author__is_suspended=False,
    ).exclude(
        author_id__in=blocked_ids
    ).exclude(
        Q(author__private_account=True)
        & ~Q(author_id__in=following_ids)
        & ~Q(author=user)
    ).select_related(
        'author',
        'shared_from',
        'shared_from__author',
    ).prefetch_related(
        'media',
        'shared_from__media',
    )


def get_diverse_feed(user, page_size=None, page=1):
    """Feed dành cho bạn — tất cả bài viết, trừ người đã block hoặc bị block."""
    if page_size is None:
        page_size = getattr(settings, 'POSTS_PER_PAGE', 12)

    offset = (page - 1) * page_size

    qs = _base_feed_queryset(user).order_by('-created_at')
    return list(qs[offset:offset + page_size])


def get_followed_feed(user, page_size=None, page=1):
    """Feed đang theo dõi — chỉ bài từ người đang follow."""
    from posts.models import Post

    if page_size is None:
        page_size = getattr(settings, 'POSTS_PER_PAGE', 12)

    following_ids = _following_ids(user)
    blocked_ids = _blocked_author_ids(user)
    offset = (page - 1) * page_size

    if not following_ids:
        return []

    qs = Post.objects.filter(
        author_id__in=following_ids,
        is_archived=False,
        author__is_suspended=False,
    ).exclude(
        author_id__in=blocked_ids
    ).select_related(
        'author',
        'shared_from',
        'shared_from__author',
    ).prefetch_related(
        'media',
        'shared_from__media',
    ).order_by('-created_at')

    return list(qs[offset:offset + page_size])


def get_followed_posts(user, count=10):
    """Lấy bài viết từ người dùng đang theo dõi."""
    return get_followed_feed(user, page_size=count, page=1)


def get_trending_posts(user, count=5):
    """Lấy bài viết thịnh hành trong 48 giờ qua."""
    from posts.models import Post
    from django.db.models import Count, F

    time_threshold = timezone.now() - timedelta(hours=48)
    blocked_ids = _blocked_author_ids(user)

    return Post.objects.filter(
        created_at__gte=time_threshold,
        is_archived=False,
        author__is_suspended=False,
    ).exclude(
        author_id__in=blocked_ids
    ).exclude(
        author=user
    ).exclude(
        author__private_account=True
    ).annotate(
        recent_likes=Count('post_likes', filter=Q(post_likes__created_at__gte=time_threshold)),
        recent_comments=Count('comments', filter=Q(comments__created_at__gte=time_threshold)),
        trending_score=F('recent_likes') * 2 + F('recent_comments') * 3,
    ).order_by('-trending_score', '-created_at')[:count]


def get_discovery_posts(user, count=5):
    """Lấy bài viết khám phá dựa trên sở thích của người dùng."""
    from posts.models import Post, Hashtag
    from django.db.models import Count, Case, When, BooleanField, Value

    user_liked_posts = Post.objects.filter(post_likes__user=user)
    user_commented_posts = Post.objects.filter(comments__author=user)
    user_interacted_posts = (user_liked_posts | user_commented_posts).distinct()

    popular_hashtags = Hashtag.objects.filter(
        posts__in=user_interacted_posts
    ).annotate(
        post_count=Count('posts')
    ).order_by('-post_count')[:10]

    blocked_ids = _blocked_author_ids(user)

    return Post.objects.filter(
        hashtags__in=popular_hashtags,
        is_archived=False,
        author__is_suspended=False,
    ).exclude(
        author_id__in=blocked_ids
    ).exclude(
        author=user
    ).exclude(
        id__in=user_interacted_posts.values('id')
    ).exclude(
        author__private_account=True
    ).annotate(
        is_liked=Case(
            When(post_likes__user=user, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).order_by('-created_at')[:count]


def get_random_posts(user, count=3):
    """Lấy bài viết ngẫu nhiên để tăng tính khám phá."""
    from posts.models import Post

    blocked_ids = _blocked_author_ids(user)

    all_post_ids = list(Post.objects.filter(
        is_archived=False,
        author__is_suspended=False,
    ).exclude(
        author_id__in=blocked_ids
    ).exclude(
        author=user
    ).exclude(
        author__private_account=True
    ).values_list('id', flat=True)[:500])

    random.shuffle(all_post_ids)
    selected_ids = all_post_ids[:min(count, len(all_post_ids))]

    if not selected_ids:
        return Post.objects.none()

    preserved_order = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(selected_ids)])
    return Post.objects.filter(id__in=selected_ids).select_related('author').prefetch_related('media').order_by(preserved_order)
