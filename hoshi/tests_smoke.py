#!/usr/bin/env python
"""Smoke test tối thiểu — chạy: python manage.py test hoshi.tests_smoke"""
from django.test import TestCase, Client
from django.conf import settings


class SmokeSettingsTests(TestCase):
    def test_secret_not_placeholder_when_not_debug_skipped(self):
        # Local DEBUG=True vẫn OK; chỉ đảm bảo settings load được
        self.assertTrue(bool(settings.SECRET_KEY))

    def test_upload_cap_reasonable(self):
        # Không cho phép 1GB mặc định nữa
        self.assertLessEqual(settings.MAX_UPLOAD_SIZE, 200 * 1024 * 1024)

    def test_home_or_login_responds(self):
        client = Client()
        resp = client.get('/')
        self.assertIn(resp.status_code, (200, 302))
