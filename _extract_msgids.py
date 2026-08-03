import re
from pathlib import Path

root = Path(r'c:\hoshi_v2\templates')
msgids = set()

for p in root.rglob('*.html'):
    text = p.read_text(encoding='utf-8', errors='ignore')
    for m in re.finditer(r"\{%\s*trans\s+'([^']+)'\s*%\}", text):
        msgids.add(m.group(1))
    for m in re.finditer(r'\{%\s*trans\s+"([^"]+)"\s*%\}', text):
        msgids.add(m.group(1))
    for m in re.finditer(r'\{%\s*blocktrans[^%]*%\}(.*?)\{%\s*endblocktrans\s*%\}', text, re.S):
        inner = m.group(1).strip()
        # Convert {{ var }} to %(var)s for gettext-style msgids
        normalized = re.sub(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}', r'%(\1)s', inner)
        normalized = ' '.join(normalized.split())
        msgids.add(normalized)

out = Path(r'c:\hoshi_v2\_msgids.txt')
out.write_text('\n'.join(sorted(msgids)), encoding='utf-8')
print(f'Found {len(msgids)} msgids -> {out}')
