from django.db.models import Q, Case, When, Count, F
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import math
import random


# Pattern ưu tiên khám phá + trending (T = viral/trending)
SLOT_PATTERN = list('RTDFTFRDTFRDTF')

RECENCY_HALF_LIFE_HOURS = 24.0
RECENCY_WEIGHT = 28.0
ENGAGEMENT_WEIGHT = 14.0
VIRAL_WEIGHT = 0.42
FOLLOW_BOOST = 18.0
AFFINITY_BOOST = 15.0
# Phạt mạnh bài đã xem gần đây → ưu tiên bài chưa thấy
SEEN_PENALTY = 55.0
CANDIDATE_MULTIPLIER = 4
CANDIDATE_MAX = 100
TOP_K_PICK = 5
# Cùng 1 bài viral không chiếm quá nhiều slot trong 1 page
MAX_TRENDING_PER_PAGE = 3


def _following_ids(user):
    return user.get_following_user_ids()


def _blocked_author_ids(user):
    return user.get_blocked_user_ids()


def _base_feed_queryset(user):
    """Queryset chung cho feed — lọc block, private account, visibility."""
    from posts.models import Post
    from posts.visibility import filter_visible_posts

    following_ids = _following_ids(user)
    blocked_ids = _blocked_author_ids(user)

    qs = Post.objects.filter(
        is_archived=False,
        author__is_suspended=False,
    ).exclude(
        author_id__in=blocked_ids
    ).exclude(
        Q(author__private_account=True)
        & ~Q(author_id__in=following_ids)
        & ~Q(author=user)
    )
    return filter_visible_posts(qs, user).select_related(
        'author',
        'shared_from',
        'shared_from__author',
    ).prefetch_related(
        'media',
        'shared_from__media',
    )


def _user_rng(user, seed=None):
    """RNG ổn định theo user (+ seed phiên để reload ra feed khác)."""
    base = (getattr(user, 'id', 0) or 0) * 10007 + 17
    if seed is not None:
        try:
            extra = int(str(seed).replace('-', '')[:12], 36) % (10 ** 9)
        except ValueError:
            extra = hash(str(seed)) % (10 ** 9)
        base = (base + extra) % (2 ** 32)
    return random.Random(base)


def _affinity_hashtag_ids(user, limit=10):
    """Hashtag từ bài user đã like/comment."""
    from posts.models import Post, Hashtag

    interacted = Post.objects.filter(
        Q(post_likes__user=user) | Q(comments__author=user)
    ).distinct()

    return list(
        Hashtag.objects.filter(posts__in=interacted)
        .annotate(post_count=Count('posts'))
        .order_by('-post_count')
        .values_list('id', flat=True)[:limit]
    )


def _score_posts(posts, following_id_set, affinity_post_ids, now=None, seen_ids=None):
    """Gắn feed_score vào từng Post (in-memory)."""
    if now is None:
        now = timezone.now()

    affinity_set = set(affinity_post_ids or [])
    seen_set = set(seen_ids or [])
    half_life = RECENCY_HALF_LIFE_HOURS

    for post in posts:
        age_hours = max((now - post.created_at).total_seconds() / 3600.0, 0.0)
        recency = math.pow(0.5, age_hours / half_life)

        engagement = (
            (post.likes_count or 0) * 2
            + (post.comments_count or 0) * 3
            + (getattr(post, 'shares_count', 0) or 0) * 5
            + (getattr(post, 'saves_count', 0) or 0) * 2
        )
        eng_term = math.log1p(engagement)
        viral_term = min(float(getattr(post, 'viral_score', 0) or 0), 80.0)

        follow_boost = FOLLOW_BOOST if post.author_id in following_id_set else 0.0
        affinity = AFFINITY_BOOST if post.id in affinity_set else 0.0
        seen_penalty = SEEN_PENALTY if post.id in seen_set else 0.0
        # Thưởng nhẹ bài chưa xem
        fresh_boost = 8.0 if post.id not in seen_set else 0.0

        post.feed_score = (
            RECENCY_WEIGHT * recency
            + ENGAGEMENT_WEIGHT * eng_term
            + VIRAL_WEIGHT * viral_term
            + follow_boost
            + affinity
            + fresh_boost
            - seen_penalty
        )

    return posts


def _sort_by_score(posts, rng=None, prefer_unseen=False, seen_ids=None):
    """Sắp theo score giảm dần; jitter đủ lớn để xáo khi engagement gần bằng nhau."""
    seen_set = set(seen_ids or []) if prefer_unseen else set()

    def sort_key(post, jitter=0.0):
        score = getattr(post, 'feed_score', 0) + jitter
        # Bài chưa xem lên trước khi điểm gần bằng
        unseen_rank = 0 if post.id not in seen_set else 1
        return (unseen_rank, -score, -post.created_at.timestamp())

    if rng is None:
        return sorted(posts, key=lambda p: sort_key(p))

    decorated = []
    for post in posts:
        jitter = rng.random() * 22.0
        decorated.append((sort_key(post, jitter), post))
    decorated.sort(key=lambda x: x[0])
    return [item[1] for item in decorated]


def _pool_followed(user, following_ids, limit):
    if not following_ids or limit <= 0:
        return []
    qs = _base_feed_queryset(user).filter(author_id__in=following_ids).order_by('-created_at')
    return list(qs[:limit])


def _pool_trending(user, limit, exclude_ids=None):
    """Bài viral/trending 48h gần đây + bài admin ép viral."""
    if limit <= 0:
        return []
    exclude_ids = exclude_ids or set()
    time_threshold = timezone.now() - timedelta(hours=48)
    qs = (
        _base_feed_queryset(user)
        .filter(Q(created_at__gte=time_threshold) | Q(admin_promoted=True))
        .exclude(id__in=exclude_ids)
        .annotate(
            recent_likes=Count(
                'post_likes',
                filter=Q(post_likes__created_at__gte=time_threshold),
            ),
            recent_comments=Count(
                'comments',
                filter=Q(comments__created_at__gte=time_threshold),
            ),
            open_reports=Count(
                'reports',
                filter=Q(reports__is_resolved=False),
            ),
            trending_score=(
                F('viral_score') * 3
                + F('recent_likes') * 2
                + F('recent_comments') * 3
                + F('shares_count') * 4
                + F('saves_count') * 2
                - F('open_reports') * 10
            ),
        )
        .filter(Q(trending_score__gt=0) | Q(admin_promoted=True))
        .order_by('-admin_promoted', '-trending_score', '-viral_score', '-created_at')
    )
    return list(qs[:limit])


def _pool_discovery(user, affinity_tag_ids, limit, exclude_ids=None):
    if limit <= 0:
        return []
    exclude_ids = exclude_ids or set()

    qs = _base_feed_queryset(user).exclude(id__in=exclude_ids).exclude(author=user)

    if affinity_tag_ids:
        qs = (
            qs.filter(hashtags__id__in=affinity_tag_ids)
            .annotate(tag_hits=Count('hashtags', filter=Q(hashtags__id__in=affinity_tag_ids)))
            .order_by('-tag_hits', '-created_at')
            .distinct()
        )
    else:
        qs = qs.order_by('-likes_count', '-comments_count', '-created_at')

    return list(qs[:limit])


def _pool_random(user, limit, exclude_ids=None, rng=None):
    if limit <= 0:
        return []
    exclude_ids = exclude_ids or set()
    if rng is None:
        rng = random

    candidate_ids = list(
        _base_feed_queryset(user)
        .exclude(id__in=exclude_ids)
        .exclude(author=user)
        .order_by('-created_at')
        .values_list('id', flat=True)[:500]
    )
    if not candidate_ids:
        return []

    rng.shuffle(candidate_ids)
    selected = candidate_ids[: min(limit, len(candidate_ids))]
    posts = list(_base_feed_queryset(user).filter(id__in=selected))
    by_id = {p.id: p for p in posts}
    return [by_id[i] for i in selected if i in by_id]


def _affinity_post_ids(user, affinity_tag_ids, limit=200):
    if not affinity_tag_ids:
        return set()
    return set(
        _base_feed_queryset(user)
        .filter(hashtags__id__in=affinity_tag_ids)
        .values_list('id', flat=True)
        .distinct()[:limit]
    )


def _can_append(result, post, max_consecutive_same_author=2):
    if not result:
        return True
    author_id = post.author_id
    streak = 0
    for prev in reversed(result):
        if prev.author_id == author_id:
            streak += 1
        else:
            break
    return streak < max_consecutive_same_author


def _take_from_pool(pool, used_ids, result, rng=None, top_k=TOP_K_PICK):
    """Lấy 1 bài từ top-K ứng viên hợp lệ (không luôn lấy #1)."""
    if not pool:
        return None

    candidates = []
    for idx, post in enumerate(pool):
        if post.id in used_ids:
            continue
        if _can_append(result, post):
            candidates.append(idx)
            if len(candidates) >= top_k:
                break

    if not candidates:
        for idx, post in enumerate(pool):
            if post.id not in used_ids:
                candidates.append(idx)
                if len(candidates) >= top_k:
                    break

    if not candidates:
        return None

    if rng is None or len(candidates) == 1:
        pick_idx = candidates[0]
    else:
        # Trọng số giảm dần: vị trí 0 nặng hơn nhưng không độc chiếm
        weights = [max(top_k - i, 1) for i in range(len(candidates))]
        pick_idx = rng.choices(candidates, weights=weights, k=1)[0]

    return pool.pop(pick_idx)


def _interleave_pools(pools, page_size, pattern=None, rng=None):
    """
    Xen kẽ theo slot pattern.
    pools: dict key -> list[Post] đã sort theo score.
    """
    if pattern is None:
        pattern = list(SLOT_PATTERN)
    else:
        pattern = list(pattern)

    # Xoay điểm bắt đầu pattern theo seed → bài mở đầu không luôn cùng pool/cùng bài
    if rng is not None and pattern:
        rotate_by = rng.randrange(len(pattern))
        pattern = pattern[rotate_by:] + pattern[:rotate_by]

    used_ids = set()
    result = []
    trending_used = 0
    key_map = {'F': 'follow', 'T': 'trending', 'D': 'discovery', 'R': 'random'}
    fallback_order = ['follow', 'trending', 'discovery', 'random']
    # Đôi khi đảo luôn thứ tự fallback để slot đầu đa dạng hơn
    if rng is not None:
        fallback_order = list(fallback_order)
        rng.shuffle(fallback_order)

    working = {k: list(v) for k, v in pools.items()}

    slot_index = 0
    guard = 0
    max_guard = page_size * 20

    while len(result) < page_size and guard < max_guard:
        guard += 1
        slot = pattern[slot_index % len(pattern)]
        slot_index += 1
        primary = key_map.get(slot, 'follow')

        # Giới hạn số bài trending/viral trong 1 page
        if primary == 'trending' and trending_used >= MAX_TRENDING_PER_PAGE:
            primary = 'discovery'

        # Vị trí đầu trang: top_k lớn hơn để tránh "bài số 1" đứng mãi
        top_k = TOP_K_PICK + 3 if len(result) == 0 else TOP_K_PICK

        post = _take_from_pool(
            working.get(primary, []), used_ids, result, rng=rng, top_k=top_k
        )
        if post is None:
            for key in fallback_order:
                if key == primary:
                    continue
                if key == 'trending' and trending_used >= MAX_TRENDING_PER_PAGE:
                    continue
                post = _take_from_pool(
                    working.get(key, []), used_ids, result, rng=rng, top_k=top_k
                )
                if post is not None:
                    primary = key
                    break

        if post is None:
            break

        used_ids.add(post.id)
        if primary == 'trending' or float(getattr(post, 'viral_score', 0) or 0) >= 12:
            trending_used += 1
        result.append(post)

    return result


def get_diverse_feed(user, page_size=None, page=1, seed=None, seen_ids=None):
    """
    Feed "Dành cho bạn": xen kẽ follow / trending / discovery / random
    với điểm recency + engagement + follow boost + hashtag affinity.

    seed: chuỗi/số từ frontend — cùng seed giữ pagination ổn định trong 1 phiên,
    seed mới (mỗi lần reload trang) → thứ tự feed đổi.
    seen_ids: bài đã xem gần đây — bị hạ điểm để luôn ưu tiên nội dung mới.
    """
    if page_size is None:
        page_size = getattr(settings, 'POSTS_PER_PAGE', 12)

    page = max(int(page or 1), 1)
    rng = _user_rng(user, seed=seed)
    following_ids = _following_ids(user)
    following_set = set(following_ids)
    raw_seen = seen_ids or []
    seen_ids = set()
    for x in raw_seen:
        try:
            seen_ids.add(int(x))
        except (TypeError, ValueError):
            continue

    # Đủ candidate cho page hiện tại + buffer
    stream_size = page * page_size
    candidate_n = min(
        max(stream_size + page_size, page_size * CANDIDATE_MULTIPLIER),
        max(CANDIDATE_MAX, stream_size + page_size),
    )
    pool_limit = candidate_n

    affinity_tags = _affinity_hashtag_ids(user)
    affinity_ids = _affinity_post_ids(user, affinity_tags)

    follow_posts = _pool_followed(user, following_ids, pool_limit)
    used = {p.id for p in follow_posts}

    trending_posts = _pool_trending(user, pool_limit, exclude_ids=used)
    used.update(p.id for p in trending_posts)

    discovery_posts = _pool_discovery(user, affinity_tags, pool_limit, exclude_ids=used)
    used.update(p.id for p in discovery_posts)

    # Nhiều random hơn để đổi mới
    random_posts = _pool_random(user, max(page_size * 2, 12), exclude_ids=used, rng=rng)

    now = timezone.now()
    for group in (follow_posts, trending_posts, discovery_posts, random_posts):
        _score_posts(group, following_set, affinity_ids, now=now, seen_ids=seen_ids)

    pools = {
        'follow': _sort_by_score(follow_posts, rng, prefer_unseen=True, seen_ids=seen_ids),
        'trending': _sort_by_score(trending_posts, rng, prefer_unseen=True, seen_ids=seen_ids),
        'discovery': _sort_by_score(discovery_posts, rng, prefer_unseen=True, seen_ids=seen_ids),
        'random': _sort_by_score(random_posts, rng, prefer_unseen=True, seen_ids=seen_ids),
    }

    pattern = SLOT_PATTERN * (max(stream_size // len(SLOT_PATTERN), 1) + 2)

    full_pools = {k: list(v) for k, v in pools.items()}
    stream = _interleave_pools(full_pools, stream_size, pattern=pattern, rng=rng)

    # Fallback chronological nếu stream thiếu
    if len(stream) < stream_size:
        have = {p.id for p in stream}
        filler = list(
            _base_feed_queryset(user)
            .exclude(id__in=have)
            .order_by('-created_at')[: stream_size - len(stream) + page_size]
        )
        _score_posts(filler, following_set, affinity_ids, now=now, seen_ids=seen_ids)
        filler = _sort_by_score(filler, rng, prefer_unseen=True, seen_ids=seen_ids)
        for post in filler:
            if len(stream) >= stream_size:
                break
            if post.id in have:
                continue
            if not _can_append(stream, post):
                continue
            have.add(post.id)
            stream.append(post)
        if len(stream) < stream_size:
            for post in filler:
                if len(stream) >= stream_size:
                    break
                if post.id in have:
                    continue
                have.add(post.id)
                stream.append(post)

    offset = (page - 1) * page_size
    return stream[offset:offset + page_size]


def get_followed_feed(user, page_size=None, page=1):
    """Feed đang theo dõi — chỉ bài từ người đang follow (chronological)."""
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
    return _pool_trending(user, count)


def get_discovery_posts(user, count=5):
    """Lấy bài viết khám phá dựa trên sở thích của người dùng."""
    from posts.models import Post

    affinity_tags = _affinity_hashtag_ids(user)
    interacted_ids = set(
        Post.objects.filter(
            Q(post_likes__user=user) | Q(comments__author=user)
        ).values_list('id', flat=True)
    )
    posts = _pool_discovery(user, affinity_tags, count + 20, exclude_ids=interacted_ids)
    return posts[:count]


def get_random_posts(user, count=3):
    """Lấy bài viết ngẫu nhiên để tăng tính khám phá."""
    return _pool_random(user, count, rng=random)
