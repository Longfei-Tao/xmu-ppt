"""Shared template catalog and explicit, project-scoped selection gate."""
from contextlib import contextmanager
import argparse
import base64
import hashlib
import json
import mimetypes
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

DECKS = Path(__file__).resolve().parents[1] / 'templates/decks'
INDEX = DECKS / 'catalog.json'
GATE_FILE = Path(__file__).resolve().parents[3] / 'output' / '.selection.json'


def catalog():
    """Built-in decks actually usable in this installation.

    The skill-only release ZIP ships no ``preview.png`` and no ``source.pptx``
    (they are outside the MIT grant, see LICENSE-ASSETS), but it does ship the
    SVG layouts. Such decks stay selectable through the SVG route instead of
    disappearing from the picker.
    """
    decks = json.loads(INDEX.read_text(encoding='utf-8'))
    available = []
    for deck in decks:
        folder = DECKS / deck['id']
        has_cover = (folder / 'preview.png').is_file()
        has_svg = any((folder / name).is_file()
                      for name in ('01_cover.svg', '03_content.svg'))
        if not (has_cover or has_svg):
            continue
        native = all((folder / name).is_file() for name in
                     ('source.pptx', 'source.slide_library.json', 'layout_index.json'))
        routes = (['svg'] if has_svg else []) + (['native'] if native else [])
        if not routes:
            continue
        deck['routes'] = routes
        deck['preview'] = (f"previews/{deck['number']:02d}.png" if has_cover
                           else f"previews/{deck['number']:02d}-cover.svg")
        available.append(deck)
    return available


def preview_svg(number, page):
    """Embed local images so previews work identically on Pages and localhost."""
    deck = next((d for d in catalog() if d['number'] == number), None)
    files = {'cover': '01_cover.svg', 'content': '03_content.svg',
             'chapter': '02_chapter.svg'}
    if deck is None or page not in files:
        raise ValueError('Unknown template preview')
    folder = DECKS / deck['id']
    path = folder / files[page]
    if not path.is_file():
        raise ValueError('Preview unavailable')
    root = ET.fromstring(path.read_bytes())
    for element in root.iter():
        for attr in ('href', '{http://www.w3.org/1999/xlink}href'):
            href = element.get(attr)
            if not href or href.startswith('data:') or href.startswith('#'):
                continue
            asset = (folder / href).resolve()
            if not asset.is_relative_to(folder.resolve()):
                raise ValueError('Preview asset outside template')
            mime = mimetypes.guess_type(asset.name)[0] or 'application/octet-stream'
            element.set(attr, f'data:{mime};base64,' + base64.b64encode(asset.read_bytes()).decode('ascii'))
    xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    return b'\n'.join(line.rstrip() for line in xml.split(b'\n'))


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def _locked(folder):
    """OS locks release automatically if a writer process exits unexpectedly."""
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / '.template-selection.lock').open('a+b') as stream:
        stream.write(b'0')
        stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def prepare(project):
    folder = Path(project) / 'confirm_ui'
    with _locked(folder):
        path = folder / 'recommendations.json'
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('kind') != 'template':
                raise ValueError('This project already has another confirmation flow')
            return data
        if (folder / 'result.json').exists():
            raise ValueError('An existing result needs a separate project')
        data = {'kind': 'template', 'request_id': secrets.token_urlsafe(24), 'recommended': []}
        _write(path, data)
        return data


def _validate(template_id, route):
    deck = next((d for d in catalog() if d['id'] == template_id), None)
    if deck is None:
        # Local-only external decks are not in the public catalogue.
        try:
            from external_selection import find_by_id
            deck = find_by_id(template_id)
        except (ImportError, OSError, ValueError):
            deck = None
    if deck is None or route not in deck['routes']:
        raise ValueError('Unknown template or unsupported authoring route')
    return deck


def _bridge_gate(deck, template_id, route, source):
    """把项目级选择同步到 idea_to_ppt 的全局门禁，避免两套流程各说各话。"""
    gate = {
        'status': 'confirmed',
        'template_id': template_id,
        'serial': deck.get('serial') or f"{int(deck.get('number', 0)):03d}",
        'selection': str(deck.get('number') or template_id),
        'template_name': deck.get('name'),
        'page_count': deck.get('page_count'),
        'route': route,
        'source': source,
        'confirmed_at': datetime.now(timezone.utc).isoformat(),
        'note': '由模板选择页 confirm 写入，供 idea_to_ppt 的 build 门禁校验。',
    }
    _write(GATE_FILE, gate)


def confirm(project, request_id, template_id, route, source):
    folder = Path(project) / 'confirm_ui'
    request = json.loads((folder / 'recommendations.json').read_text(encoding='utf-8'))
    if request.get('kind') != 'template' or not secrets.compare_digest(str(request.get('request_id', '')), str(request_id)):
        raise ValueError('Expired selection request. Reopen the project gallery')
    deck = _validate(template_id, route)
    if source not in ('browser', 'chat', 'delegated'):
        raise ValueError('Unknown selection source')
    with _locked(folder):
        path = folder / 'result.json'
        if path.exists():
            previous = selected(project)
            if (previous['template_id'], previous['route'], previous['source']) == (template_id, route, source):
                return previous
            raise ValueError('Selection is locked. Use a new project to change templates')
        result = {'kind': 'template', 'stage': 'final', 'status': 'confirmed',
                  'request_id': request_id, 'template_id': template_id,
                  'route': route, 'source': source,
                  'confirmed_at': datetime.now(timezone.utc).isoformat()}
        if deck.get('namespace') == 'external':
            from external_selection import source_path
            origin = source_path(template_id)
            if origin is None:
                raise ValueError('本机模板原件不存在，请重新扫描模板目录')
            result['namespace'] = 'external'
            result['serial'] = deck.get('serial')
            result['source_path'] = str(origin)
        _write(path, result)
        _bridge_gate(deck, template_id, route, source)
        return result


def selected(project):
    folder = Path(project) / 'confirm_ui'
    try:
        request = json.loads((folder / 'recommendations.json').read_text(encoding='utf-8'))
        result = json.loads((folder / 'result.json').read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError('Waiting for explicit template selection') from exc
    if (request.get('kind') != 'template' or result.get('kind') != 'template'
            or result.get('status') != 'confirmed'
            or result.get('request_id') != request.get('request_id')):
        raise ValueError('No current confirmed template selection')
    _validate(result.get('template_id'), result.get('route'))
    return result


def require_selection(project, route, source=None):
    """Gate opted-in projects while preserving existing export-only projects."""
    marker = Path(project) / 'confirm_ui/recommendations.json'
    if not marker.exists():
        return
    request = json.loads(marker.read_text(encoding='utf-8'))
    if request.get('kind') != 'template':
        return
    result = selected(project)
    if result['route'] != route:
        raise ValueError('Export route differs from the confirmed selection')
    if source is not None:
        expected = (Path(result['source_path'])
                    if result.get('namespace') == 'external' and result.get('source_path')
                    else DECKS / result['template_id'] / 'source.pptx')
        if hashlib.sha256(Path(source).read_bytes()).digest() != hashlib.sha256(expected.read_bytes()).digest():
            raise ValueError('Source PPTX differs from the confirmed template')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list', 'prepare', 'confirm', 'check'])
    parser.add_argument('project', nargs='?', type=Path)
    parser.add_argument('--template')
    parser.add_argument('--route', choices=['svg', 'native'], default='svg')
    parser.add_argument('--source', choices=['chat', 'delegated'], default='chat')
    args = parser.parse_args()
    try:
        if args.action == 'list':
            result = catalog()
        else:
            if args.project is None:
                parser.error('project is required')
            if args.action == 'prepare':
                result = prepare(args.project)
            elif args.action == 'check':
                result = selected(args.project)
            else:
                request = prepare(args.project)
                result = confirm(args.project, request['request_id'], args.template, args.route, args.source)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
