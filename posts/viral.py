"""
Viral / trending helpers cho feed Moora.

- views_count: mỗi user chỉ đếm 1 lần / vài giờ (cache debounce)
- viral_score: velocity × recency − report penalty
- is_trending: viral_score đủ cao và bài còn mới
"""
from __future__ import annotations

import math
from datetime import timedelta

from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

# Điểm tối thiểu để hiện badge "Đang thịnh hành"
TRENDING_SCORE_THRESHOLD = 12.0
TRENDING_MAX_AGE_HOURS = 48
# Mỗi user chỉ ghi impression 1 lần trong cửa sổ này
IMPRESSION_DEDUP_SECONDS = 6 * 60 * 60
# Không recompute viral_score quá dày
VIRAL_RECOMPUTE_MIN_SECONDS = 45

VIRAL_HALF_LIFE_HOURS = 12.0
LIKE_WEIGHT = 2.0
COMMENT_WEIGHT = 3.0
SHARE_WEIGHT = 5.0
SAVE_WEIGHT = 2.0
REPORT_PENALTY_EACH = 8.0
REPORT_PENALTY_CAP = 45.0
# Điểm mặc định khi admin đẩy viral
ADMIN_PROMOTE_SCORE = 80.0


def _impression_cache_key(user_id: int, post_id: int) -> str:
    return f'post:imp:{user_id}:{post_id}'


def _viral_lock_key(post_id: int) -> str:
    return f'post:viral:lock:{post_id}'


def compute_viral_score(
    *,
    likes_count: int = 0,
    comments_count: int = 0,
    shares_count: int = 0,
    saves_count: int = 0,
    views_count: int = 0,
    created_at=None,
    report_count: int = 0,
    now=None,
) -> float:
    """Tính điểm viral (không ghi DB)."""
    if now is None:
        now = timezone.now()
    if created_at is None:
        created_at = now

    age_hours = max((now - created_at).total_seconds() / 3600.0, 0.0)
    if age_hours > TRENDING_MAX_AGE_HOURS * 1.5:
        # Quá cũ → gần như không viral nữa
        return 0.0

    engagement = (
        (likes_count or 0) * LIKE_WEIGHT
        + (comments_count or 0) * COMMENT_WEIGHT
        + (shares_count or 0) * SHARE_WEIGHT
        + (saves_count or 0) * SAVE_WEIGHT
    )
    views = max(int(views_count or 0), 1)
    # Engagement / log(views): viral thật = nhiều tương tác so với lượt xem
    rate = engagement / math.log1p(views)
    recency = math.pow(0.5, age_hours / VIRAL_HALF_LIFE_HOURS)
    # Thưởng nhẹ khi vừa mới có nhiều tương tác (engagement tuyệt đối)
    burst = math.log1p(engagement) * 1.8

    report_penalty = min((report_count or 0) * REPORT_PENALTY_EACH, REPORT_PENALTY_CAP)
    score = (rate * 28.0 + burst) * recency - report_penalty
    return max(round(score, 3), 0.0)


def is_post_trending(post) -> bool:
    if getattr(post, 'admin_promoted', False):
        return True
    score = float(getattr(post, 'viral_score', 0) or 0)
    if score < TRENDING_SCORE_THRESHOLD:
        return False
    created = getattr(post, 'created_at', None)
    if not created:
        return False
    age_h = (timezone.now() - created).total_seconds() / 3600.0
    return age_h <= TRENDING_MAX_AGE_HOURS


def _admin_score_floor(post) -> float:
    """Sàn điểm khi admin promote — tránh refresh_viral_score hạ xuống."""
    if not getattr(post, 'admin_promoted', False):
        return 0.0
    boost = float(getattr(post, 'admin_viral_boost', 0) or 0)
    return boost if boost > 0 else ADMIN_PROMOTE_SCORE


def _open_report_count(post_id: int) -> int:
    from posts.models import PostReport

    return PostReport.objects.filter(
        post_id=post_id,
        is_resolved=False,
    ).count()


def refresh_viral_score(post_or_id, force: bool = False) -> float:
    """Cập nhật viral_score trên Post (có debounce)."""
    from posts.models import Post

    post_id = getattr(post_or_id, 'id', post_or_id)
    if not post_id:
        return 0.0

    lock = _viral_lock_key(post_id)
    if not force and cache.get(lock):
        post = Post.objects.filter(pk=post_id).only('viral_score').first()
        return float(getattr(post, 'viral_score', 0) or 0) if post else 0.0

    post = Post.objects.filter(pk=post_id).first()
    if not post:
        return 0.0

    score = compute_viral_score(
        likes_count=post.likes_count,
        comments_count=post.comments_count,
        shares_count=post.shares_count,
        saves_count=post.saves_count,
        views_count=post.views_count,
        created_at=post.created_at,
        report_count=_open_report_count(post_id),
    )
    floor = _admin_score_floor(post)
    if floor > 0:
        score = max(score, floor)
    Post.objects.filter(pk=post_id).update(
        viral_score=score,
        viral_score_updated_at=timezone.now(),
    )
    cache.set(lock, 1, timeout=VIRAL_RECOMPUTE_MIN_SECONDS)
    return score


def promote_post_viral(post_or_id, score: float | None = None) -> float:
    """Admin đẩy bài lên viral/trending."""
    from posts.models import Post

    post_id = getattr(post_or_id, 'id', post_or_id)
    floor = float(score) if score is not None else ADMIN_PROMOTE_SCORE
    floor = max(floor, TRENDING_SCORE_THRESHOLD)
    Post.objects.filter(pk=post_id).update(
        admin_promoted=True,
        admin_viral_boost=floor,
        viral_score=floor,
        viral_score_updated_at=timezone.now(),
    )
    cache.delete(_viral_lock_key(post_id))
    return floor


def demote_post_viral(post_or_id) -> float:
    """Admin gỡ ép viral — tính lại điểm tự nhiên."""
    from posts.models import Post

    post_id = getattr(post_or_id, 'id', post_or_id)
    Post.objects.filter(pk=post_id).update(
        admin_promoted=False,
        admin_viral_boost=0.0,
    )
    cache.delete(_viral_lock_key(post_id))
    return refresh_viral_score(post_id, force=True)


def record_impressions(user, post_ids) -> int:
    """
    Ghi nhận bài hiện trong viewport.
    Trả về số bài thực sự tăng view.
    """
    from posts.models import Post, UserInteraction

    if not user or not getattr(user, 'is_authenticated', False):
        return 0

    ids = []
    for raw in post_ids or []:
        try:
            pid = int(raw)
        except (TypeError, ValueError):
            continue
        if pid > 0 and pid not in ids:
            ids.append(pid)
        if len(ids) >= 40:
            break

    if not ids:
        return 0

    counted = 0
    newly = []
    for pid in ids:
        key = _impression_cache_key(user.id, pid)
        if cache.get(key):
            continue
        cache.set(key, 1, timeout=IMPRESSION_DEDUP_SECONDS)
        newly.append(pid)

    if not newly:
        return 0

    # Tăng counter + interaction (bulk)
    updated = Post.objects.filter(id__in=newly).update(views_count=F('views_count') + 1)
    counted = updated

    UserInteraction.objects.bulk_create(
        [
            UserInteraction(user=user, post_id=pid, interaction_type='view', duration=0)
            for pid in newly
        ],
        ignore_conflicts=True,
        batch_size=40,
    )

    # Recompute viral cho vài bài (không block quá lâu)
    for pid in newly[:12]:
        try:
            refresh_viral_score(pid, force=False)
        except Exception:
            continue

    return counted


def bump_share_count(post_id: int, amount: int = 1) -> None:
    from posts.models import Post

    Post.objects.filter(pk=post_id).update(shares_count=F('shares_count') + amount)
    refresh_viral_score(post_id, force=True)


def bump_save_count(post_id: int, delta: int) -> None:
    from posts.models import Post

    Post.objects.filter(pk=post_id).update(saves_count=F('saves_count') + delta)
    # Không cho âm
    Post.objects.filter(pk=post_id, saves_count__lt=0).update(saves_count=0)
    refresh_viral_score(post_id, force=True)


def on_engagement_changed(post_id: int) -> None:
    """Gọi sau like / comment / report."""
    refresh_viral_score(post_id, force=True)
