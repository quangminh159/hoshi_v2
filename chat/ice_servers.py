"""Cấu hình ICE/STUN/TURN tự host (coturn) cho WebRTC.

Ưu tiên hạ tầng của bạn — không bắt buộc bên thứ 3.
- TURN_HOST / TURN_URLS + TURN_USERNAME + TURN_CREDENTIAL (coturn Docker)
- Tùy chọn: ICE_SERVERS_JSON override
- Metered chỉ còn hỗ trợ nếu bạn chủ động set METERED_* (không khuyến nghị)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_metered_cache: dict[str, Any] = {'at': 0, 'servers': None}
_METERED_CACHE_TTL = 45 * 60


def _split_urls(raw: str) -> list[str]:
    return [part.strip() for part in (raw or '').replace(';', ',').split(',') if part.strip()]


def _ephemeral_turn_credential(secret: str, ttl_seconds: int = 3600) -> tuple[str, str]:
    expiry = int(time.time()) + max(60, int(ttl_seconds or 3600))
    username = str(expiry)
    digest = hmac.new(secret.encode('utf-8'), username.encode('utf-8'), hashlib.sha1).digest()
    credential = base64.b64encode(digest).decode('ascii')
    return username, credential


def _urls_from_host(host: str) -> list[str]:
    host = (host or '').strip().rstrip('/')
    if not host:
        return []
    if host.startswith('turn:') or host.startswith('turns:') or host.startswith('stun:'):
        return [host]
    host = host.replace('https://', '').replace('http://', '').split('/')[0]
    # Coturn: STUN + TURN cùng cổng 3478 (UDP/TCP)
    return [
        f'stun:{host}:3478',
        f'turn:{host}:3478',
        f'turn:{host}:3478?transport=tcp',
    ]


def _entry_has_turn(entry: dict[str, Any]) -> bool:
    urls = entry.get('urls')
    if isinstance(urls, str):
        return urls.startswith('turn')
    if isinstance(urls, list):
        return any(str(u).startswith('turn') for u in urls)
    return False


def _fetch_metered_ice_servers() -> list[dict[str, Any]] | None:
    """Tùy chọn — chỉ khi bạn set METERED_* (mặc định không dùng)."""
    api_key = (getattr(settings, 'METERED_TURN_API_KEY', '') or '').strip()
    if not api_key:
        return None

    now = time.time()
    if _metered_cache['servers'] and (now - _metered_cache['at']) < _METERED_CACHE_TTL:
        return list(_metered_cache['servers'])

    url = (getattr(settings, 'METERED_TURN_CREDENTIALS_URL', '') or '').strip()
    if not url:
        app = (getattr(settings, 'METERED_TURN_APP_NAME', '') or '').strip()
        if not app:
            return None
        url = f'https://{app}.metered.live/api/v1/turn/credentials?apiKey={api_key}'
    elif 'apiKey=' not in url:
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}apiKey={api_key}'

    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        servers = None
        if isinstance(data, list) and data:
            servers = data
        elif isinstance(data, dict) and isinstance(data.get('iceServers'), list):
            servers = data['iceServers']
        if servers:
            _metered_cache['at'] = now
            _metered_cache['servers'] = servers
            return list(servers)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.warning('Metered TURN fetch failed: %s', exc)
    return None


def _configured_turn_entry() -> dict[str, Any] | None:
    turn_urls = _split_urls(getattr(settings, 'TURN_URLS', '') or '')
    if not turn_urls:
        turn_urls = _urls_from_host(getattr(settings, 'TURN_HOST', '') or '')

    username = (getattr(settings, 'TURN_USERNAME', '') or '').strip()
    credential = (getattr(settings, 'TURN_CREDENTIAL', '') or '').strip()
    secret = (getattr(settings, 'TURN_SECRET', '') or '').strip()
    ttl = int(getattr(settings, 'TURN_CREDENTIAL_TTL', 3600) or 3600)

    if not turn_urls:
        return None

    if secret and not (username and credential):
        username, credential = _ephemeral_turn_credential(secret, ttl)

    entry: dict[str, Any] = {
        'urls': turn_urls if len(turn_urls) > 1 else turn_urls[0],
    }
    if username and credential:
        entry['username'] = username
        entry['credential'] = credential
    return entry


def build_ice_servers() -> list[dict[str, Any]]:
    raw_json = getattr(settings, 'ICE_SERVERS_JSON', '') or ''
    if raw_json.strip():
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict) and 'iceServers' in parsed:
                servers = parsed['iceServers']
            else:
                servers = parsed
            if isinstance(servers, list) and servers:
                return servers
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    servers: list[dict[str, Any]] = []
    seen_turn = False

    # 1) Coturn / TURN của bạn
    turn_entry = _configured_turn_entry()
    if turn_entry:
        servers.append(turn_entry)
        seen_turn = True

    # 2) Metered chỉ nếu chủ động cấu hình (không khuyến nghị)
    metered = _fetch_metered_ice_servers()
    if metered:
        servers.extend(metered)
        seen_turn = seen_turn or any(
            isinstance(s, dict) and _entry_has_turn(s) for s in metered
        )

    if not seen_turn:
        logger.warning(
            'Chưa cấu hình TURN tự host — gọi khác mạng sẽ thất bại. '
            'Chạy coturn + set TURN_HOST (xem huong_dan_turn.txt).'
        )

    return servers


def ice_servers_payload() -> dict[str, Any]:
    servers = build_ice_servers()
    has_turn = any(isinstance(s, dict) and _entry_has_turn(s) for s in servers)
    policy = (getattr(settings, 'WEBRTC_ICE_TRANSPORT_POLICY', '') or 'all').strip().lower()
    if policy not in ('all', 'relay'):
        policy = 'all'
    if has_turn and getattr(settings, 'WEBRTC_PREFER_RELAY', False):
        policy = 'relay'
    return {
        'iceServers': servers,
        'has_turn': has_turn,
        'iceTransportPolicy': policy,
    }
