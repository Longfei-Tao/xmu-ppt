"""Build the public template gallery from the installable skill's assets."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/xmu-ppt/scripts'
sys.path.insert(0, str(SCRIPTS))
from template_selection import catalog, preview_svg, DECKS


def build():
    destination = ROOT / 'docs/templates'
    (destination / 'static').mkdir(parents=True, exist_ok=True)
    (destination / 'previews').mkdir(exist_ok=True)
    source = SCRIPTS / 'confirm_ui/static'
    html = (source / 'gallery.html').read_text(encoding='utf-8')
    (destination / 'index.html').write_text(html.replace('<html lang="zh-CN">', '<html lang="zh-CN" data-mode="published">'), encoding='utf-8')
    for name in ('gallery.css', 'gallery.js'):
        shutil.copyfile(source / name, destination / 'static' / name)
    decks = catalog()
    (destination / 'catalog.json').write_text(json.dumps(decks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for deck in decks:
        number = deck['number']
        if deck['preview'].endswith('.png'):
            shutil.copyfile(DECKS / deck['id'] / 'preview.png', destination / deck['preview'])
        for page in ('cover', 'content', 'chapter'):
            (destination / f'previews/{number:02d}-{page}.svg').write_bytes(preview_svg(number, page))
    print(f'Built gallery with {len(decks)} templates')


if __name__ == '__main__':
    build()
