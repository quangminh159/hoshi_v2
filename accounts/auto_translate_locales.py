"""
Hoàn thiện i18n Moora (không cần GNU gettext):
1) Quét msgid từ {% trans %}, blocktrans, gettext/_
2) Merge vào locale/*/LC_MESSAGES/django.po (giữ bản dịch cũ)
3) Dịch chỗ trống bằng Google + cache
4) Ghi django.po + django.mo

Chạy:
  .\\venv\\Scripts\\python.exe -u accounts\\auto_translate_locales.py
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import polib
from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parents[1]
LOCALE_DIR = ROOT / 'locale'
CACHE_FILE = ROOT / 'accounts' / '_translation_cache.json'
MSGIDS_DUMP = ROOT / '_msgids.txt'

LANG_FOLDERS = {
    'en': 'en',
    'ja': 'ja',
    'ko': 'ko',
    'zh_Hans': 'zh-CN',
}

OVERRIDES = {
    'en': {
        'Cài đặt': 'Settings',
        'Ngôn ngữ': 'Language',
        'Đăng xuất': 'Log out',
        'Đăng nhập': 'Log in',
        'Đăng ký': 'Sign up',
        'Trang cá nhân': 'Profile',
        'Trang chủ': 'Home',
        'Thông báo': 'Notifications',
        'Tin nhắn': 'Messages',
        'Đã lưu': 'Saved',
        'Đã thích': 'Liked',
        'Bảng tin': 'Feed',
        'Dành cho bạn': 'For you',
        'Đang theo dõi': 'Following',
        'Theo dõi': 'Follow',
        'Ghim': 'Pin',
        'Bỏ ghim': 'Unpin',
        'Tắt thông báo': 'Mute notifications',
        'Bật thông báo': 'Unmute notifications',
        'Xóa': 'Delete',
        'Rời nhóm': 'Leave group',
        'Xóa cuộc trò chuyện': 'Delete conversation',
        'Đã cập nhật ngôn ngữ hiển thị.': 'Display language updated.',
        'Cài đặt ngôn ngữ': 'Language settings',
        'Lưu ngôn ngữ': 'Save language',
        'Cuộc gọi thoại': 'Voice call',
        'Cuộc gọi video': 'Video call',
        'Đang đổ chuông...': 'Ringing...',
        'Đang kết nối...': 'Connecting...',
        'Đang trong cuộc gọi': 'In call',
        'Trả lời': 'Answer',
        'Từ chối': 'Decline',
        'Thêm': 'More',
        '%(time)s trước': '%(time)s ago',
    },
    'ja': {
        'Cài đặt': '設定',
        'Ngôn ngữ': '言語',
        'Đăng xuất': 'ログアウト',
        'Đăng nhập': 'ログイン',
        'Đăng ký': '登録',
        'Trang cá nhân': 'プロフィール',
        'Trang chủ': 'ホーム',
        'Thông báo': '通知',
        'Tin nhắn': 'メッセージ',
        'Dành cho bạn': 'おすすめ',
        'Đang theo dõi': 'フォロー中',
        'Theo dõi': 'フォロー',
        'Ghim': 'ピン留め',
        'Bỏ ghim': 'ピンを外す',
        'Tắt thông báo': '通知をオフ',
        'Bật thông báo': '通知をオン',
        'Xóa': '削除',
        'Rời nhóm': 'グループを退会',
        'Đã cập nhật ngôn ngữ hiển thị.': '表示言語を更新しました。',
    },
    'ko': {
        'Cài đặt': '설정',
        'Ngôn ngữ': '언어',
        'Đăng xuất': '로그아웃',
        'Đăng nhập': '로그인',
        'Đăng ký': '회원가입',
        'Trang cá nhân': '프로필',
        'Trang chủ': '홈',
        'Thông báo': '알림',
        'Tin nhắn': '메시지',
        'Dành cho bạn': '추천',
        'Đang theo dõi': '팔로잉',
        'Theo dõi': '팔로우',
        'Ghim': '고정',
        'Bỏ ghim': '고정 해제',
        'Tắt thông báo': '알림 끄기',
        'Bật thông báo': '알림 켜기',
        'Xóa': '삭제',
        'Rời nhóm': '그룹 나가기',
        'Đã cập nhật ngôn ngữ hiển thị.': '표시 언어가 업데이트되었습니다.',
    },
    'zh_Hans': {
        'Cài đặt': '设置',
        'Ngôn ngữ': '语言',
        'Đăng xuất': '退出登录',
        'Đăng nhập': '登录',
        'Đăng ký': '注册',
        'Trang cá nhân': '个人主页',
        'Trang chủ': '首页',
        'Thông báo': '通知',
        'Tin nhắn': '私信',
        'Dành cho bạn': '推荐',
        'Đang theo dõi': '正在关注',
        'Theo dõi': '关注',
        'Ghim': '置顶',
        'Bỏ ghim': '取消置顶',
        'Tắt thông báo': '关闭通知',
        'Bật thông báo': '开启通知',
        'Xóa': '删除',
        'Rời nhóm': '退出群组',
        'Đã cập nhật ngôn ngữ hiển thị.': '显示语言已更新。',
    },
}

SKIP_DIRS = {
    'venv', '.venv', 'node_modules', '.git', '__pycache__', 'media', 'staticfiles',
    'migrations', '.cursor', 'locale', 'accounts',  # skip this script + cache noise
}

# Only simple quoted {% trans "..." %} / {% trans '...' %}
TRANS_RE = re.compile(r"""\{%\s*trans\s+(?P<q>['"])(?P<s>.*?)(?P=q)\s*%\}""", re.DOTALL)
# blocktrans with optional trimmed content (keep placeholders as %(name)s when possible)
BLOCK_RE = re.compile(
    r"""\{%\s*blocktrans(?P<head>[^%]*)%\}(?P<body>.*?)\{%\s*endblocktrans\s*%\}""",
    re.DOTALL,
)
GETTEXT_RE = re.compile(
    r"""(?:gettext_lazy|_)\(\s*(?P<q>['"])(?P<s>.*?)(?P=q)\s*\)""",
    re.DOTALL,
)
GETTEXT_CALL_RE = re.compile(
    r"""(?:translation\.gettext|gettext)\(\s*(?P<q>['"])(?P<s>.*?)(?P=q)\s*\)""",
    re.DOTALL,
)


def unescape_quoted(s: str) -> str:
    """Chỉ unescape escape thông thường — không unicode_escape (làm hỏng UTF-8 tiếng Việt)."""
    return (
        s.replace(r'\\', '\0')
        .replace(r'\n', '\n')
        .replace(r'\t', '\t')
        .replace(r"\'", "'")
        .replace(r'\"', '"')
        .replace('\0', '\\')
    )


def looks_garbled(s: str) -> bool:
    # Mojibake markers / private-use / too many replacement chars
    if '\ufffd' in s:
        return True
    if 'A�' in s or 'Ã' in s and 'Â' in s:
        return True
    return False


def clean_msgid(s: str) -> str | None:
    s = unescape_quoted(s).strip()
    if not s or looks_garbled(s):
        return None
    if len(s) > 350:
        return None
    if '{% plural %}' in s:
        s = s.split('{% plural %}', 1)[0].strip()
    s = re.sub(r'[ \t]+\n', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    if not s or looks_garbled(s):
        return None
    return s


def normalize_blocktrans(body: str) -> str | None:
    body = body.strip()
    if not body:
        return None
    # {{ var }} -> %(var)s ; drop other tags
    body = re.sub(r'\{\{\s*([a-zA-Z_][\w.]*)\s*(?:\|[^}]*)?\}\}', r'%(\1)s', body)
    body = re.sub(r'\{%.*?%\}', '', body)
    body = re.sub(r'\s+', ' ', body).strip()
    # simplify dotted names: user.username -> username-ish keep as-is if simple
    body = re.sub(r'%\(([^\)]*\.[^\)]*)\)s', '%(var)s', body)
    return clean_msgid(body)


def scan_codebase() -> list[str]:
    found: set[str] = set()
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        # Don't scan the translate script itself if under accounts - already skipped accounts dir
        # Actually we skipped all accounts - that drops model verbose_name translations from accounts!
        # Fix: only skip auto_translate and cache
        suffix = path.suffix.lower()
        if suffix not in {'.html', '.txt', '.py'}:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue

        if suffix in {'.html', '.txt'}:
            for m in TRANS_RE.finditer(text):
                msgid = clean_msgid(m.group('s'))
                if msgid:
                    found.add(msgid)
            for m in BLOCK_RE.finditer(text):
                msgid = normalize_blocktrans(m.group('body'))
                if msgid:
                    found.add(msgid)
        else:
            for pattern in (GETTEXT_RE, GETTEXT_CALL_RE):
                for m in pattern.finditer(text):
                    msgid = clean_msgid(m.group('s'))
                    if msgid:
                        found.add(msgid)

    # Keep valid msgids already in PO catalogs
    for folder in LANG_FOLDERS:
        po_path = LOCALE_DIR / folder / 'LC_MESSAGES' / 'django.po'
        if not po_path.exists():
            continue
        po = polib.pofile(str(po_path))
        for entry in po:
            if not entry.msgid:
                continue
            msgid = clean_msgid(entry.msgid)
            if msgid:
                found.add(msgid)

    ordered = sorted(found)
    MSGIDS_DUMP.write_text('\n'.join(ordered) + '\n', encoding='utf-8')
    return ordered


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')


def existing_po_map(folder: str) -> dict[str, str]:
    po_path = LOCALE_DIR / folder / 'LC_MESSAGES' / 'django.po'
    mapping: dict[str, str] = {}
    if not po_path.exists():
        return mapping
    po = polib.pofile(str(po_path))
    for entry in po:
        if not entry.msgid:
            continue
        msgid = clean_msgid(entry.msgid)
        if not msgid:
            continue
        msgstr = (entry.msgstr or '').strip()
        if '{% plural %}' in msgstr:
            msgstr = msgstr.split('{% plural %}', 1)[0].strip()
        if msgstr and not looks_garbled(msgstr):
            mapping[msgid] = msgstr
    return mapping


def translate_batch(texts: list[str], target_code: str, on_progress=None) -> dict[str, str]:
    translator = GoogleTranslator(source='vi', target=target_code)
    results: dict[str, str] = {}
    for i, text in enumerate(texts):
        try:
            translated = translator.translate(text) or text
            results[text] = translated
        except Exception as exc:
            try:
                safe = text.encode('ascii', 'backslashreplace').decode('ascii')[:70]
                print(f'  fail [{target_code}] {type(exc).__name__}: {safe}', flush=True)
            except Exception:
                print(f'  fail [{target_code}] {type(exc).__name__}', flush=True)
            results[text] = text
        if (i + 1) % 30 == 0:
            print(f'  {target_code}: {i + 1}/{len(texts)}', flush=True)
            if on_progress:
                on_progress(results)
            time.sleep(0.3)
        else:
            time.sleep(0.03)
    return results


def build_po(folder: str, mapping: dict[str, str]) -> None:
    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': 'moora',
        'Language': folder.replace('_', '-'),
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
        'Plural-Forms': 'nplurals=2; plural=(n != 1);',
    }
    for msgid in sorted(mapping.keys()):
        msgstr = mapping.get(msgid) or ''
        if '{% plural %}' in msgstr:
            msgstr = msgstr.split('{% plural %}', 1)[0].strip()
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))

    dest = LOCALE_DIR / folder / 'LC_MESSAGES'
    dest.mkdir(parents=True, exist_ok=True)
    po.save(str(dest / 'django.po'))
    po.save_as_mofile(str(dest / 'django.mo'))
    empty = sum(1 for e in po if not (e.msgstr or '').strip())
    print(f'Wrote {folder}: {len(po)} entries, empty={empty}', flush=True)


def main() -> None:
    # Re-enable scanning accounts models/forms (verbose_name) but skip this script
    global SKIP_DIRS
    SKIP_DIRS = {
        'venv', '.venv', 'node_modules', '.git', '__pycache__', 'media', 'staticfiles',
        'migrations', '.cursor', 'locale',
    }

    print('Scanning msgids...', flush=True)
    # Custom scan that skips only this file
    found: set[str] = set()
    skip_files = {Path(__file__).resolve(), CACHE_FILE.resolve()}
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.resolve() in skip_files:
            continue
        suffix = path.suffix.lower()
        if suffix not in {'.html', '.txt', '.py'}:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        if suffix in {'.html', '.txt'}:
            for m in TRANS_RE.finditer(text):
                msgid = clean_msgid(m.group('s'))
                if msgid:
                    found.add(msgid)
            for m in BLOCK_RE.finditer(text):
                msgid = normalize_blocktrans(m.group('body'))
                if msgid:
                    found.add(msgid)
        else:
            for pattern in (GETTEXT_RE, GETTEXT_CALL_RE):
                for m in pattern.finditer(text):
                    msgid = clean_msgid(m.group('s'))
                    if msgid:
                        found.add(msgid)

    for folder in LANG_FOLDERS:
        po_path = LOCALE_DIR / folder / 'LC_MESSAGES' / 'django.po'
        if po_path.exists():
            po = polib.pofile(str(po_path))
            for entry in po:
                msgid = clean_msgid(entry.msgid) if entry.msgid else None
                if msgid:
                    found.add(msgid)

    msgids = sorted(found)
    MSGIDS_DUMP.write_text('\n'.join(msgids) + '\n', encoding='utf-8')
    print(f'Found {len(msgids)} msgids', flush=True)

    cache = load_cache()
    # Drop garbled cache keys
    for folder in list(cache.keys()):
        cleaned = {
            k: v for k, v in cache.get(folder, {}).items()
            if isinstance(k, str) and isinstance(v, str) and not looks_garbled(k) and not looks_garbled(v)
        }
        cache[folder] = cleaned
    save_cache(cache)

    for folder, google_code in LANG_FOLDERS.items():
        print(f'\n=== {folder} ({google_code}) ===', flush=True)
        mapping = existing_po_map(folder)
        lang_cache = cache.get(folder, {})
        for msgid in msgids:
            if not (mapping.get(msgid) or '').strip() and (lang_cache.get(msgid) or '').strip():
                mapping[msgid] = lang_cache[msgid]

        missing = [m for m in msgids if not (mapping.get(m) or '').strip()]
        if missing:
            print(f'Translating {len(missing)} missing...', flush=True)

            def _progress(partial):
                lang_cache.update(partial)
                cache[folder] = lang_cache
                save_cache(cache)

            freshly = translate_batch(missing, google_code, on_progress=_progress)
            mapping.update(freshly)
            lang_cache.update(freshly)
            cache[folder] = lang_cache
            save_cache(cache)
        else:
            print('No missing strings', flush=True)

        for msgid in msgids:
            mapping.setdefault(msgid, '')
        mapping.update(OVERRIDES.get(folder, {}))
        build_po(folder, mapping)

    print('\nDone.', flush=True)


if __name__ == '__main__':
    main()
