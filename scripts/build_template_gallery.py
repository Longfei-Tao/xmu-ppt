"""Build the public template gallery from the installable skill's built-in assets.

The public gallery intentionally ships only the 15 built-in decks. External
decks are a local-only capability and must never be published as covers or
originals; pass --include-external only for a private local preview.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/xmu-ppt/scripts'
sys.path.insert(0, str(SCRIPTS))
from template_selection import catalog, preview_svg, DECKS


def external_decks(destination):
    """Copy external covers for a private local-only preview build."""
    gallery = ROOT / 'local-gallery/catalog.js'
    if not gallery.is_file():
        return []
    text = gallery.read_text(encoding='utf-8')
    data = json.loads(text[text.index('=') + 1:].strip().rstrip(';'))
    (destination / 'previews/external').mkdir(parents=True, exist_ok=True)
    decks = []
    for deck in data.get('templates', []):
        if deck.get('namespace') == 'builtin':
            continue
        cover = ROOT / 'local-gallery' / deck.get('cover', '')
        if not cover.is_file():
            continue
        relative = f'previews/external/{deck["number"]:03d}.webp'
        shutil.copyfile(cover, destination / relative)
        decks.append({
            'number': deck['number'],
            'id': deck['id'],
            'name': deck['name'],
            'style': deck.get('style', ''),
            'tags': deck.get('tags', []),
            'serial': deck.get('serial') or f'{deck["number"]:03d}',
            'routes': ['native'],
            'namespace': 'external',
            'preview': relative,
        })
    return decks


def build(include_external=False):
    destination = ROOT / 'docs/templates'
    (destination / 'static').mkdir(parents=True, exist_ok=True)
    (destination / 'previews').mkdir(exist_ok=True)
    source = SCRIPTS / 'confirm_ui/static'
    html = (source / 'gallery.html').read_text(encoding='utf-8')
    (destination / 'index.html').write_text(html.replace('<html lang="zh-CN">', '<html lang="zh-CN" data-mode="published">'), encoding='utf-8')
    for name in ('gallery.css', 'gallery.js'):
        shutil.copyfile(source / name, destination / 'static' / name)
    decks = catalog()
    for deck in decks:
        number = deck['number']
        if deck['preview'].endswith('.png'):
            shutil.copyfile(DECKS / deck['id'] / 'preview.png', destination / deck['preview'])
        for page in ('cover', 'content', 'chapter'):
            (destination / f'previews/{number:02d}-{page}.svg').write_bytes(preview_svg(number, page))
    external_dir = destination / 'previews/external'
    if include_external:
        decks += external_decks(destination)
    elif external_dir.exists():
        shutil.rmtree(external_dir)
    decks.sort(key=lambda d: d['number'])
    (destination / 'catalog.json').write_text(json.dumps(decks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Built gallery with {len(decks)} templates '
          f'({len(decks) - 15} external)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build the public gallery from built-in decks only.')
    parser.add_argument('--include-external', action='store_true',
                        help='private local preview only: merge external covers from local-gallery')
    args = parser.parse_args()
    build(include_external=args.include_external)
