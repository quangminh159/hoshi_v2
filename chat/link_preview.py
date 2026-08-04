"""Lấy metadata (OG / oEmbed) để hiện card preview khi chia sẻ link trong chat."""

from __future__ import annotations

import ipaddress
import re
import socket
from html import unescape
from urllib.parse import urlparse, urljoin

import requests
from django.core.cache import cache

URL_RE = re.compile(r'https?://[^\s<>\'"\])}>]+', re.IGNORECASE)
META_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']([^"\']+)["\'][^>]+content=["\']([^"\']*)["\'][^>]*>|'
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']([^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)

CACHE_TTL = 60 * 60 * 12  # 12 giờ
REQUEST_TIMEOUT = 4
MAX_HTML_BYTES = 350_000
USER_AGENT = (
    'Mozilla/5.0 (compatible; HoshiLinkPreview/1.0; +https://hoshi.local)'
)


def extract_first_url(text: str | None) -> str | None:
    if not text:
        return None
    match = URL_RE.search(text)
    if not match:
        return None
    url = match.group(0).rstrip('.,;:!?)】」』"\'')
    return url or None


def _host_is_private(hostname: str) -> bool:
    if not hostname:
        return True
    host = hostname.lower().strip('.')
    if host in {'localhost', '127.0.0.1', '::1'} or host.endswith('.local'):
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return True
    return False


def is_safe_public_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {'http', 'https'}:
        return False
    if not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    return not _host_is_private(parsed.hostname)


def _youtube_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if host in {'youtu.be'}:
        return parsed.path.lstrip('/').split('/')[0] or None
    if 'youtube.com' in host or 'youtube-nocookie.com' in host:
        if parsed.path.startswith('/watch'):
            from urllib.parse import parse_qs
            qs = parse_qs(parsed.query)
            vids = qs.get('v') or []
            return vids[0] if vids else None
        parts = [p for p in parsed.path.split('/') if p]
        if parts and parts[0] in {'shorts', 'embed', 'live', 'v'} and len(parts) > 1:
            return parts[1]
    return None


def _fetch_youtube(url: str) -> dict | None:
    try:
        resp = requests.get(
            'https://www.youtube.com/oembed',
            params={'url': url, 'format': 'json'},
            timeout=REQUEST_TIMEOUT,
            headers={'User-Agent': USER_AGENT},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        thumb = data.get('thumbnail_url') or ''
        # Prefer higher-res thumb when possible
        vid = _youtube_id(url)
        if vid:
            thumb = f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg'
        return {
            'url': url,
            'title': (data.get('title') or 'YouTube').strip(),
            'description': (data.get('author_name') or '').strip(),
            'image': thumb,
            'site_name': data.get('provider_name') or 'YouTube',
        }
    except Exception:
        return None


def _parse_meta(html: str) -> dict:
    tags: dict[str, str] = {}
    for match in META_RE.finditer(html):
        if match.group(1) and match.group(2) is not None:
            key, val = match.group(1), match.group(2)
        else:
            key, val = match.group(4), match.group(3)
        if key and val is not None:
            tags[key.lower()] = unescape(val.strip())
    title_match = TITLE_RE.search(html)
    page_title = unescape(title_match.group(1).strip()) if title_match else ''
    return {
        'title': tags.get('og:title') or tags.get('twitter:title') or page_title,
        'description': tags.get('og:description') or tags.get('twitter:description') or tags.get('description') or '',
        'image': tags.get('og:image') or tags.get('twitter:image') or tags.get('twitter:image:src') or '',
        'site_name': tags.get('og:site_name') or '',
    }


def _fetch_open_graph(url: str) -> dict | None:
    try:
        with requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                'User-Agent': USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml',
            },
            stream=True,
            allow_redirects=True,
        ) as resp:
            final_url = resp.url
            if not is_safe_public_url(final_url):
                return None
            if resp.status_code >= 400:
                return None
            content_type = (resp.headers.get('Content-Type') or '').lower()
            if 'html' not in content_type and 'text/' not in content_type:
                # Có thể là ảnh trực tiếp
                if content_type.startswith('image/'):
                    host = urlparse(final_url).hostname or ''
                    return {
                        'url': final_url,
                        'title': host,
                        'description': '',
                        'image': final_url,
                        'site_name': host,
                    }
                return None

            chunks = []
            size = 0
            for chunk in resp.iter_content(chunk_size=16384):
                if not chunk:
                    continue
                chunks.append(chunk)
                size += len(chunk)
                if size >= MAX_HTML_BYTES:
                    break
            html = b''.join(chunks).decode('utf-8', errors='ignore')

        meta = _parse_meta(html)
        title = (meta.get('title') or '').strip()
        if not title:
            title = urlparse(final_url).hostname or final_url
        image = (meta.get('image') or '').strip()
        if image:
            image = urljoin(final_url, image)
        site = (meta.get('site_name') or urlparse(final_url).hostname or '').strip()
        return {
            'url': final_url,
            'title': title[:200],
            'description': (meta.get('description') or '')[:240],
            'image': image,
            'site_name': site[:80],
        }
    except Exception:
        return None


def get_link_preview(url: str) -> dict | None:
    url = (url or '').strip()
    if not url or not is_safe_public_url(url):
        return None

    cache_key = f'link_preview:v1:{url}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

    preview = None
    if _youtube_id(url):
        preview = _fetch_youtube(url)
    if not preview:
        preview = _fetch_open_graph(url)

    # Cache cả miss (False) để tránh spam request lỗi
    cache.set(cache_key, preview or False, CACHE_TTL)
    return preview
