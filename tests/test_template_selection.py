"""Template selection must be explicit, current and supported by real assets."""
import json
import sys
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/xmu-ppt/scripts'
sys.path.insert(0, str(SCRIPTS))
CACHE = SCRIPTS.parents[2] / '.cache'
CACHE.mkdir(exist_ok=True)


class SelectionTests(unittest.TestCase):
    def test_concurrent_identical_confirmation_is_idempotent(self):
        from template_selection import prepare, confirm
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            project = Path(tmp)
            with ThreadPoolExecutor(max_workers=4) as pool:
                requests = list(pool.map(lambda _: prepare(project), range(4)))
            self.assertEqual(len({r['request_id'] for r in requests}), 1)
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: confirm(project, requests[0]['request_id'],
                                   '厦门大学_官方_厦园晴日', 'svg', 'browser'), range(4)))
            self.assertTrue(all(result == results[0] for result in results))

    def test_catalog_matches_assets(self):
        from template_selection import catalog
        decks = catalog()
        self.assertEqual(len(decks), 15)
        self.assertEqual(sum('native' in d['routes'] for d in decks), 14)
        self.assertEqual(len({d['number'] for d in decks}), 15)

    def test_pending_and_confirmation(self):
        from template_selection import prepare, confirm, selected
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            project = Path(tmp)
            request = prepare(project)
            with self.assertRaises(ValueError):
                selected(project)
            result = confirm(project, request['request_id'], '厦门大学_官方_厦园晴日', 'svg', 'chat')
            self.assertEqual(selected(project)['template_id'], result['template_id'])
            self.assertEqual(confirm(project, request['request_id'], result['template_id'], 'svg', 'chat'), result)
            with self.assertRaises(ValueError):
                confirm(project, request['request_id'], '厦门大学_主题_晚霞', 'svg', 'chat')

    def test_invalid_and_stale_choices(self):
        from template_selection import prepare, confirm
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            project = Path(tmp)
            request = prepare(project)
            for token, deck, route in [('old', '厦门大学_官方_厦园晴日', 'svg'),
                                       (request['request_id'], '../secret', 'svg'),
                                       (request['request_id'], '厦门大学_官方_南强蔚蓝', 'native')]:
                with self.assertRaises(ValueError):
                    confirm(project, token, deck, route, 'browser')
            self.assertFalse((project / 'confirm_ui/result.json').exists())

    def test_export_gate_preserves_legacy_and_blocks_pending(self):
        from template_selection import prepare, confirm, require_selection
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            project = Path(tmp)
            require_selection(project, 'svg')
            request = prepare(project)
            with self.assertRaises(ValueError):
                require_selection(project, 'svg')
            confirm(project, request['request_id'], '厦门大学_官方_厦园晴日', 'svg', 'chat')
            require_selection(project, 'svg')
            with self.assertRaises(ValueError):
                require_selection(project, 'native')

    def test_browser_flow_and_generic_endpoint_cannot_bypass(self):
        from template_selection import prepare, selected
        from confirm_ui.server import create_app
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            project = Path(tmp)
            request = prepare(project)
            client = create_app(str(project), idle_timeout=0).test_client()
            with client.get('/') as response:
                self.assertIn('gallery.js', response.get_data(as_text=True))
            self.assertEqual(len(client.get('/api/templates').json), 15)
            self.assertEqual(client.post('/api/confirm', json={'status': 'confirmed'}).status_code, 400)
            payload = dict(request_id=request['request_id'], template_id='厦门大学_主题_晚霞', route='svg')
            self.assertEqual(client.post('/api/template-confirm', json=payload).status_code, 200)
            self.assertEqual(selected(project)['source'], 'browser')
            self.assertEqual(client.get('/previews/09-content.svg').status_code, 200)
            self.assertEqual(client.get('/previews/99-content.svg').status_code, 404)

    def test_normal_export_commands_block_pending_selection(self):
        from template_selection import prepare
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            project = Path(tmp)
            prepare(project)
            for command in ([str(SCRIPTS / 'svg_to_pptx.py'), str(project)],
                            [str(SCRIPTS / 'template_fill_pptx.py'), 'apply', 'missing.pptx',
                             str(project / 'fill_plan.json'), '-o', str(project / 'out.pptx')]):
                result = subprocess.run([sys.executable, *command], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'Waiting for explicit template selection', result.stderr)
            self.assertFalse(list(project.glob('*.pptx')))

    def test_native_source_must_match_confirmed_template(self):
        from template_selection import prepare, confirm, require_selection, DECKS
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            project = Path(tmp)
            request = prepare(project)
            deck = '厦门大学_官方_厦园晴日'
            confirm(project, request['request_id'], deck, 'native', 'chat')
            require_selection(project, 'native', DECKS / deck / 'source.pptx')
            with self.assertRaisesRegex(ValueError, 'Source PPTX differs'):
                require_selection(project, 'native', DECKS / '厦门大学_主题_晚霞/source.pptx')

    def test_public_gallery_uses_shared_assets(self):
        from template_selection import catalog, preview_svg
        public = SCRIPTS.parents[2] / 'docs/templates'
        self.assertEqual(json.loads((public / 'catalog.json').read_text(encoding='utf-8')), catalog())
        for name in ('gallery.css', 'gallery.js'):
            self.assertEqual((public / 'static' / name).read_bytes(),
                             (SCRIPTS / 'confirm_ui/static' / name).read_bytes())
        for deck in catalog():
            self.assertTrue((public / deck['preview']).exists())
            for page in ('content', 'chapter'):
                exported = (public / f"previews/{deck['number']:02d}-{page}.svg").read_text(encoding='utf-8')
                generated = preview_svg(deck['number'], page).decode('utf-8')
                # Other exporter tests register equivalent XML namespace prefixes.
                self.assertEqual(ET.canonicalize(exported, rewrite_prefixes=True),
                                 ET.canonicalize(generated, rewrite_prefixes=True))


if __name__ == '__main__':
    unittest.main()
