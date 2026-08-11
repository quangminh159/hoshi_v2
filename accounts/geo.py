"""
Định vị thiết bị đăng nhập.

Ưu tiên độ chính xác:
1. GPS / Wi‑Fi của trình duyệt (Geolocation API) — mét
2. Geo theo IP (thành phố / quận) — km
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

IP_GEO_CACHE_SECONDS = 24 * 60 * 60
REVERSE_GEO_CACHE_SECONDS = 30 * 24 * 60 * 60
REQUEST_TIMEOUT = 3.5


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return True
    return (
        ip.startswith('127.')
        or ip.startswith('10.')
        or ip.startswith('192.168.')
        or ip.startswith('172.')
        or ip == '::1'
        or ip.startswith('fc')
        or ip.startswith('fd')
        or ip.startswith('fe80')
    )


def lookup_ip_location(ip: str) -> dict[str, Any] | None:
    """
    Tra cứu vị trí theo IP (ip-api.com, miễn phí).
    Trả về dict: city, region, country, country_code, lat, lon, label, accuracy_m
    """
    if not ip or _is_private_ip(ip):
        return {
            'city': '',
            'region': '',
            'country': 'Mạng nội bộ',
            'country_code': '',
            'lat': None,
            'lon': None,
            'label': 'Mạng nội bộ / localhost',
            'accuracy_m': None,
            'source': 'ip',
        }

    cache_key = f'device:ipgeo:v1:{ip}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = None
    try:
        # fields rút gọn; lang=vi
        url = (
            f'http://ip-api.com/json/{ip}'
            f'?fields=status,message,country,countryCode,regionName,city,lat,lon,query'
            f'&lang=vi'
        )
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = resp.json() if resp.ok else {}
        if data.get('status') == 'success':
            city = (data.get('city') or '').strip()
            region = (data.get('regionName') or '').strip()
            country = (data.get('country') or '').strip()
            parts = [p for p in (city, region, country) if p]
            result = {
                'city': city,
                'region': region,
                'country': country,
                'country_code': (data.get('countryCode') or '').strip(),
                'lat': data.get('lat'),
                'lon': data.get('lon'),
                'label': ', '.join(parts) if parts else ip,
                # IP geo thường sai lệch vài km → ~5–50km
                'accuracy_m': 25000.0,
                'source': 'ip',
            }
    except Exception as exc:
        logger.debug('IP geo failed for %s: %s', ip, exc)

    cache.set(cache_key, result, timeout=IP_GEO_CACHE_SECONDS)
    return result


def reverse_geocode(lat: float, lon: float) -> dict[str, Any] | None:
    """Đổi toạ độ → địa chỉ (Nominatim / OpenStreetMap)."""
    try:
        lat_f = round(float(lat), 5)
        lon_f = round(float(lon), 5)
    except (TypeError, ValueError):
        return None

    cache_key = f'device:revgeo:v1:{lat_f}:{lon_f}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = None
    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={
                'format': 'jsonv2',
                'lat': lat_f,
                'lon': lon_f,
                'zoom': 16,
                'addressdetails': 1,
                'accept-language': 'vi',
            },
            headers={
                'User-Agent': 'MooraDeviceSecurity/1.0 (security; contact=noreply@moora.vn)',
            },
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json() if resp.ok else {}
        addr = data.get('address') or {}
        city = (
            addr.get('city')
            or addr.get('town')
            or addr.get('village')
            or addr.get('municipality')
            or addr.get('suburb')
            or ''
        )
        region = addr.get('state') or addr.get('region') or addr.get('county') or ''
        country = addr.get('country') or ''
        country_code = (addr.get('country_code') or '').upper()
        road = addr.get('road') or addr.get('neighbourhood') or addr.get('quarter') or ''
        parts = [p for p in (road, city, region, country) if p]
        label = data.get('display_name') or ', '.join(parts)
        # Rút gọn label nếu quá dài
        if label and len(label) > 180:
            label = ', '.join(parts) if parts else label[:180]
        result = {
            'city': city,
            'region': region,
            'country': country,
            'country_code': country_code,
            'lat': lat_f,
            'lon': lon_f,
            'label': label or f'{lat_f}, {lon_f}',
            'source': 'gps',
        }
    except Exception as exc:
        logger.debug('Reverse geocode failed: %s', exc)
        result = {
            'city': '',
            'region': '',
            'country': '',
            'country_code': '',
            'lat': lat_f,
            'lon': lon_f,
            'label': f'{lat_f}, {lon_f}',
            'source': 'gps',
        }

    cache.set(cache_key, result, timeout=REVERSE_GEO_CACHE_SECONDS)
    return result
