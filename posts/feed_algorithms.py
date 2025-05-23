from django.db.models import Count, Q, F, Case, When, BooleanField, Value
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import random
import logging

def get_diverse_feed(user, page_size=None, page=1):
    """
    Tạo feed đa dạng bằng cách kết hợp nhiều loại bài viết khác nhau
    """
    from posts.models import Post, Like  # Import ở đây tránh circular import
    
    # Sử dụng page_size từ tham số, nếu không thì sử dụng từ settings, nếu không thì dùng mặc định
    if page_size is None:
        page_size = getattr(settings, 'POSTS_PER_PAGE', 12)  # Mặc định 12 bài viết
    
    logger = logging.getLogger(__name__)
    logger.info(f"get_diverse_feed called with page_size={page_size}, page={page}")
    
    # Lấy tất cả bài viết từ database trước
    all_posts = Post.objects.filter(
        is_archived=False,
        author__is_suspended=False
    ).exclude(
        author__in=user.blocked_users.all()
    ).exclude(
        author__in=user.blocked_by.all()
    ).exclude(
        author__private_account=True,  # Loại bỏ bài viết từ tài khoản riêng tư
        author__in=user.following.all(),  # Trừ khi đang follow tài khoản đó
    ).order_by('-created_at')
    
    # Thêm bài viết từ các tài khoản đang theo dõi vào đầu danh sách
    followed_posts = Post.objects.filter(
        author__in=user.following.all(),
        is_archived=False,
        author__is_suspended=False
    ).exclude(
        author__in=user.blocked_users.all()
    ).exclude(
        author__in=user.blocked_by.all()
    ).order_by('-created_at')
    
    # Kết hợp bài viết theo dõi ở đầu và bài viết khác ở sau
    combined_posts = list(followed_posts)
    for post in all_posts:
        if post.id not in [p.id for p in combined_posts]:
            combined_posts.append(post)
    
    total_posts = len(combined_posts)
    logger.info(f"Tổng số bài viết: {total_posts}")
    
    # Tính toán offset và limit cho phân trang
    offset = (page - 1) * page_size
    
    # Nếu offset vượt quá tổng số bài viết thì thử lấy bài viết từ nguồn khác
    if offset >= total_posts:
        logger.info(f"Offset {offset} vượt quá tổng số bài viết {total_posts}, thử lấy bài viết từ nguồn khác")
        # Thử lấy bài viết trending
        trending_posts = get_trending_posts(user, count=page_size)
        if trending_posts:
            return list(trending_posts)
        # Nếu không có bài viết trending, thử lấy bài viết ngẫu nhiên
        random_posts = get_random_posts(user, count=page_size)
        return list(random_posts)
    
    # Lấy bài viết theo phạm vi trang hiện tại
    end_index = min(offset + page_size, total_posts)
    posts_for_page = combined_posts[offset:end_index]
    
    # Nếu không đủ bài viết, bổ sung thêm từ các nguồn khác
    if len(posts_for_page) < page_size:
        remaining = page_size - len(posts_for_page)
        logger.info(f"Cần bổ sung thêm {remaining} bài viết")
        
        # Thử lấy thêm bài viết từ trending
        trending_posts = get_trending_posts(user, count=remaining)
        posts_for_page.extend([p for p in trending_posts if p.id not in [post.id for post in posts_for_page]])
        
        # Nếu vẫn chưa đủ, lấy thêm bài viết ngẫu nhiên
        if len(posts_for_page) < page_size:
            remaining = page_size - len(posts_for_page)
            random_posts = get_random_posts(user, count=remaining)
            posts_for_page.extend([p for p in random_posts if p.id not in [post.id for post in posts_for_page]])
    
    logger.info(f"Offset: {offset}, End index: {end_index}, Posts for page: {len(posts_for_page)}")
    
    return posts_for_page[:page_size]  # Đảm bảo chỉ trả về đúng số lượng yêu cầu

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