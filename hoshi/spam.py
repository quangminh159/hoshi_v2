"""Rate-limit đơn giản trên Django cache (Redis khi có)."""
from __future__ import annotations

from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse


def _parse_rate(rate: str) -> tuple[int, int]:
    """'30/m' → (30, 60), '10/h' → (10, 3600), '5/s' → (5, 1)."""
    num, _, unit = rate.partition('/')
    limit = int(num)
    unit = (unit or 'm').lower()
    window = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}.get(unit, 60)
    return limit, window


def hit_rate_limit(bucket: str, rate: str = '30/m') -> bool:
    """
    True nếu ĐÃ vượt hạn (request nên bị chặn).
    False nếu còn trong hạn (cho phép).
    """
    limit, window = _parse_rate(rate)
    key = f'rl:{bucket}'
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        n = 1
    return n > limit


def client_ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or '0.0.0.0'


def ratelimit(rate: str = '30/m', key: str = 'user', methods=('POST',)):
    """Decorator cho view function-based."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if methods and request.method.upper() not in {m.upper() for m in methods}:
                return view_func(request, *args, **kwargs)

            if key == 'user' and getattr(request, 'user', None) and request.user.is_authenticated:
                ident = f'u:{request.user.pk}'
            else:
                ident = f'ip:{client_ip(request)}'

            bucket = f'{view_func.__module__}.{view_func.__name__}:{ident}'
            if hit_rate_limit(bucket, rate):
                wants_json = (
                    request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    or 'application/json' in (request.headers.get('Accept') or '')
                    or request.content_type == 'application/json'
                )
                if wants_json:
                    return JsonResponse(
                        {'status': 'error', 'message': 'Bạn thao tác quá nhanh. Thử lại sau.'},
                        status=429,
                    )
                return HttpResponse('Bạn thao tác quá nhanh. Thử lại sau.', status=429)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
