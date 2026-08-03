"""Auto-translate extracted msgids and rebuild locale catalogs."""
import re
import time
from pathlib import Path

import polib
from deep_translator import GoogleTranslator

MSGIDS_FILE = Path(r'c:\hoshi_v2\_msgids.txt')
LOCALE_DIR = Path(r'c:\hoshi_v2\locale')
CACHE_FILE = Path(r'c:\hoshi_v2\accounts\_translation_cache.json')

# Keep existing hand-tuned translations as overrides
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
        '%(time)s trước': '%(time)s ago',
    }
}

LANG_MAP = {
    'en': 'en',
    'ja': 'ja',
    'ko': 'ko',
    'zh_Hans': 'zh-CN',
}


def load_msgids():
    raw = MSGIDS_FILE.read_text(encoding='utf-8').splitlines()
    out = []
    for line in raw:
        s = line.strip()
        if not s:
            continue
        if len(s) > 220:
            continue
        if s.startswith('<!DOCTYPE') or '<html>' in s.lower():
            continue
        out.append(s)
    return out


def translate_batch(texts, target_code):
    translator = GoogleTranslator(source='vi', target=target_code)
    results = {}
    for i, text in enumerate(texts):
        # Skip pure placeholders / already English-looking short tokens
        try:
            # Preserve leading/trailing whitespace style
            translated = translator.translate(text)
            if not translated:
                translated = text
            results[text] = translated
        except Exception as exc:
            try:
                print(f'  fail [{target_code}]: idx={i} -> {type(exc).__name__}')
            except Exception:
                pass
            results[text] = text
        if (i + 1) % 20 == 0:
            print(f'  {target_code}: {i + 1}/{len(texts)}')
            time.sleep(0.4)
        else:
            time.sleep(0.05)
    return results


def build_po(lang_folder, mapping):
    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': 'hoshi',
        'Language': lang_folder.replace('_', '-'),
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
    }
    for msgid, msgstr in sorted(mapping.items()):
        # Fix common blocktrans plural leftovers
        if '{% plural %}' in msgid:
            # store as singular-style msgid without plural tag for simple cases
            parts = msgid.split('{% plural %}')
            msgid = parts[0].strip()
            if not msgstr or msgstr == msgid:
                msgstr = mapping.get(msgid, msgid)
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    dest = LOCALE_DIR / lang_folder / 'LC_MESSAGES'
    dest.mkdir(parents=True, exist_ok=True)
    po.save(dest / 'django.po')
    po.save_as_mofile(dest / 'django.mo')
    print(f'Wrote {dest} ({len(po)} entries)')


def main():
    import json
    msgids = load_msgids()
    print(f'Msgids to translate: {len(msgids)}')

    cache = {}
    if CACHE_FILE.exists():
        cache = json.loads(CACHE_FILE.read_text(encoding='utf-8'))

    for folder, google_code in LANG_MAP.items():
        print(f'\n=== {folder} ({google_code}) ===')
        lang_cache = cache.get(folder, {})
        missing = [m for m in msgids if m not in lang_cache]
        if missing:
            print(f'Translating {len(missing)} missing strings...')
            lang_cache.update(translate_batch(missing, google_code))
            cache[folder] = lang_cache
            CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
        else:
            print('Using cache')

        mapping = {m: lang_cache.get(m, m) for m in msgids}
        # Apply overrides
        for k, v in OVERRIDES.get(folder if folder != 'zh_Hans' else 'en', {}).items():
            if folder == 'en' or folder in OVERRIDES:
                pass
        for k, v in OVERRIDES.get('en' if folder == 'en' else folder, {}).items():
            mapping[k] = v
        if folder == 'en':
            mapping.update(OVERRIDES['en'])

        build_po(folder, mapping)

    print('\nDone.')


if __name__ == '__main__':
    main()
