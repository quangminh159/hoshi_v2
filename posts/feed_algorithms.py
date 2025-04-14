from django.db.models import Count, Q, F, Case, When, BooleanField, Value
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import random

def get_diverse_feed(user, page_size=10, page=1):
    """
    Tạo feed đa dạng bằng cách kết hợp nhiều loại bài viết khác nhau
    """
    from posts.models import Post, Like  # Import ở đây tránh circular import
    
    # Tỷ lệ các loại nội dung trong feed - thêm yếu tố ngẫu nhiên
    base_ratios = {
        'followed': 0.5,  # Bài viết từ người theo dõi
        'trending': 0.2,  # Bài viết xu hướng
        'discovery': 0.2,  # Bài viết khám phá
        'random': 0.1     # Bài viết ngẫu nhiên
    }
    
    # Thêm yếu tố ngẫu nhiên vào tỷ lệ (±20%)
    ratios = {}
    for key, value in base_ratios.items():
        variation = value * 0.2  # 20% variation
        ratios[key] = value + random.uniform(-variation, variation)
    
    # Chuẩn hóa tỷ lệ để tổng = 1
    total = sum(ratios.values())
    ratios = {k: v/total for k, v in ratios.items()}
    
    # Tính số lượng bài viết cần lấy cho mỗi loại
    total_needed = page_size * 2  # Lấy nhiều hơn để lọc sau
    followed_count = int(total_needed * ratios['followed'])
    trending_count = int(total_needed * ratios['trending'])
    discovery_count = int(total_needed * ratios['discovery'])
    random_count = int(total_needed * ratios['random'])
    
    # --- 1. Bài viết từ người dùng theo dõi ---
    followed_posts = get_followed_posts(user, followed_count)
    
    # --- 2. Bài viết xu hướng ---
    trending_posts = get_trending_posts(user, trending_count)
    
    # --- 3. Bài viết khám phá dựa trên sở thích ---
    discovery_posts = get_discovery_posts(user, discovery_count)
    
    # --- 4. Bài viết ngẫu nhiên ---
    random_posts = get_random_posts(user, random_count)
    
    # Kết hợp các danh sách
    combined_posts = list(followed_posts) + list(trending_posts) + list(discovery_posts) + list(random_posts)
    
    # Loại bỏ các bài viết trùng lặp
    seen_ids = set()
    unique_posts = []
    for post in combined_posts:
        if post.id not in seen_ids:
            seen_ids.add(post.id)
            unique_posts.append(post)
    
    # Trộn để không có các khối bài viết cùng loại liên tiếp nhau
    random.shuffle(unique_posts)
    
    # Tính offset cho phân trang
    offset = (page - 1) * page_size
    
    # Trả về số lượng bài viết theo trang
    return unique_posts[offset:offset+page_size]

def get_followed_posts(user, count=10):
    """Lấy bài viết từ người dùng đang theo dõi"""
    from posts.models import Post
    
    following_users = user.following.all()
    
    return Post.objects.filter(
        author__in=following_users,
        is_archived=False,
        author__is_suspended=False
    ).order_by('-created_at')[:count]

def get_trending_posts(user, count=5):
    """Lấy bài viết thịnh hành trong 48 giờ qua"""
    from posts.models import Post, Like, Comment
    
    # Thời gian để xem xét bài viết hot (48 giờ qua)
    time_threshold = timezone.now() - timedelta(hours=48)
    
    # Danh sách người dùng bị chặn hoặc chặn người dùng hiện tại
    blocked_users = list(user.blocked_users.all()) + list(user.blocked_by.all())
    
    # Lấy bài viết có nhiều lượt thích và bình luận trong 48 giờ qua
    trending_posts = Post.objects.filter(
        created_at__gte=time_threshold,
        is_archived=False,
        author__is_suspended=False
    ).exclude(
        author__in=blocked_users
    ).exclude(
        author=user  # Loại bỏ bài viết của chính người dùng
    ).exclude(
        author__private_account=True  # Loại bỏ bài viết từ tài khoản riêng tư
    ).annotate(
        recent_likes=Count('post_likes', filter=Q(post_likes__created_at__gte=time_threshold)),
        recent_comments=Count('comments', filter=Q(comments__created_at__gte=time_threshold)),
        # Tính điểm xu hướng (lượt thích x2 + bình luận x3)
        trending_score=F('recent_likes') * 2 + F('recent_comments') * 3
    ).order_by('-trending_score', '-created_at')[:count]
    
    return trending_posts

def get_discovery_posts(user, count=5):
    """Lấy bài viết khám phá dựa trên sở thích của người dùng"""
    from posts.models import Post, UserInteraction, Hashtag
    
    # Lấy các hashtag phổ biến từ bài viết người dùng đã tương tác
    user_liked_posts = Post.objects.filter(post_likes__user=user)
    user_commented_posts = Post.objects.filter(comments__author=user)
    user_interacted_posts = (user_liked_posts | user_commented_posts).distinct()
    
    # Lấy hashtag phổ biến từ các bài viết đã tương tác
    popular_hashtags = Hashtag.objects.filter(
        posts__in=user_interacted_posts
    ).annotate(
        post_count=Count('posts')
    ).order_by('-post_count')[:10]
    
    # Danh sách người dùng bị chặn hoặc chặn người dùng hiện tại
    blocked_users = list(user.blocked_users.all()) + list(user.blocked_by.all())
    
    # Lấy bài viết có chứa các hashtag phổ biến
    discovery_posts = Post.objects.filter(
        hashtags__in=popular_hashtags,
        is_archived=False,
        author__is_suspended=False
    ).exclude(
        author__in=blocked_users
    ).exclude(
        author=user
    ).exclude(
        id__in=user_interacted_posts.values('id')  # Loại bỏ bài viết đã tương tác
    ).exclude(
        author__private_account=True  # Loại bỏ bài viết từ tài khoản riêng tư
    ).annotate(
        # Thêm trường để đánh dấu đã tương tác hay chưa
        is_liked=Case(
            When(post_likes__user=user, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    ).order_by('-created_at')[:count]
    
    return discovery_posts

def get_random_posts(user, count=3):
    """Lấy bài viết ngẫu nhiên để tăng tính khám phá"""
    from posts.models import Post
    
    # Danh sách người dùng bị chặn hoặc chặn người dùng hiện tại
    blocked_users = list(user.blocked_users.all()) + list(user.blocked_by.all())
    
    # Lấy ID của tất cả bài viết hợp lệ
    all_post_ids = Post.objects.filter(
        is_archived=False,
        author__is_suspended=False
    ).exclude(
        author__in=blocked_users
    ).exclude(
        author=user
    ).exclude(
        author__private_account=True  # Loại bỏ bài viết từ tài khoản riêng tư
    ).values_list('id', flat=True)
    
    # Chọn ngẫu nhiên một số ID
    random_ids = list(all_post_ids)
    random.shuffle(random_ids)
    selected_ids = random_ids[:min(count, len(random_ids))]
    
    # Lấy các bài viết theo ID
    preserved_order = Case(*[When(id=id, then=pos) for pos, id in enumerate(selected_ids)])
    random_posts = Post.objects.filter(id__in=selected_ids).order_by(preserved_order)
    
    return random_posts 