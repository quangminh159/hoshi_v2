"""Cấu hình ICE/STUN/TURN cho WebRTC gọi thoại/video."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from django.conf import settings


DEFAULT_STUN_SERVERS = [
    {'urls': 'stun:stun.l.google.com:19302'},
    {'urls': 'stun:stun1.l.google.com:19302'},
]


def _split_urls(raw: str) -> list[str]:
    return [part.strip() for part in (raw or '').replace(';', ',').split(',') if part.strip()]


def _ephemeral_turn_credential(secret: str, ttl_seconds: int = 3600) -> tuple[str, str]:
    """
    Coturn static-auth-secret style:
    username = expiry_unix_timestamp
    credential = base64(hmac_sha1(secret, username))
    """
    expiry = int(time.time()) + max(60, int(ttl_seconds or 3600))
    username = str(expiry)
    digest = hmac.new(secret.encode('utf-8'), username.encode('utf-8'), hashlib.sha1).digest()
    credential = base64.b64encode(digest).decode('ascii')
    return username, credential


def build_ice_servers() -> list[dict[str, Any]]:
    """
    Trả về danh sách RTCIceServer cho client.

    Ưu tiên:
    1) ICE_SERVERS_JSON (JSON array đầy đủ)
    2) TURN_URLS + (TURN_USERNAME/TURN_CREDENTIAL hoặc TURN_SECRET)
    3) luôn kèm STUN mặc định
    """
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

    servers: list[dict[str, Any]] = list(DEFAULT_STUN_SERVERS)

    turn_urls = _split_urls(getattr(settings, 'TURN_URLS', '') or '')
    if not turn_urls:
        return servers

    username = (getattr(settings, 'TURN_USERNAME', '') or '').strip()
    credential = (getattr(settings, 'TURN_CREDENTIAL', '') or '').strip()
    secret = (getattr(settings, 'TURN_SECRET', '') or '').strip()
    ttl = int(getattr(settings, 'TURN_CREDENTIAL_TTL', 3600) or 3600)

    if secret and not (username and credential):
        username, credential = _ephemeral_turn_credential(secret, ttl)

    entry: dict[str, Any] = {'urls': turn_urls if len(turn_urls) > 1 else turn_urls[0]}
    if username and credential:
        entry['username'] = username
        entry['credential'] = credential
    servers.append(entry)
    return servers


def ice_servers_payload() -> dict[str, Any]:
    servers = build_ice_servers()
    has_turn = any(
        isinstance(s.get('urls'), str) and s['urls'].startswith('turn')
        or (
            isinstance(s.get('urls'), list)
            and any(str(u).startswith('turn') for u in s['urls'])
        )
        for s in servers
    )
    return {
        'iceServers': servers,
        'has_turn': has_turn,
    }
