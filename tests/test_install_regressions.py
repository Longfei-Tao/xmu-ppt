"""Fresh-install, copied-skill and dependency-update regressions."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/xmu-ppt/scripts'))
import update_repo
import template_selection as selection
import idea_to_ppt as flow


class InstallRegressionTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.cache').mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / '.cache')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        state = mock.patch.object(update_repo, 'DEPENDENCY_STATE_DIR', self.folder, create=True)
        state.start()
        self.addCleanup(state.stop)

    def test_missing_svg_assets_are_not_offered_as_usable(self):
        deck = self.folder / 'example'
        deck.mkdir()
        (deck / '01_cover.svg').write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><image href="missing.png"/></svg>',
            encoding='utf-8')
        index = self.folder / 'catalog.json'
        index.write_text(json.dumps([{'id': 'example', 'number': 1}]), encoding='utf-8')
        with mock.patch.object(selection, 'DECKS', self.folder), \
                mock.patch.object(selection, 'INDEX', index):
            self.assertEqual(selection.catalog(), [])

    def test_project_confirmation_survives_another_project(self):
        with mock.patch.object(selection, 'GATE_FILE', self.folder / 'gate.json'), \
                mock.patch.object(flow, 'GATE_FILE', self.folder / 'gate.json'):
            first = self.folder / 'first'
            second = self.folder / 'second'
            first_id = '厦门大学_官方_厦园晴日'
            second_id = '厦门大学_主题_晚霞'
            for project, template in ((first, first_id), (second, second_id)):
                request = selection.prepare(project)
                selection.confirm(project, request['request_id'], template, 'native', 'chat')
            gate = flow.require_confirmed({'template_id': first_id}, project=first)
            self.assertEqual(gate['template_id'], first_id)
            plan_file = first / 'plan.json'
            plan_file.write_text(json.dumps({'template_id': first_id}), encoding='utf-8')
            with mock.patch.object(flow, 'resolve_source', side_effect=RuntimeError('gate passed')):
                with self.assertRaisesRegex(RuntimeError, 'gate passed'):
                    flow.build(plan_file, first / 'out.pptx')
            analysis = first / 'analysis'
            analysis.mkdir()
            nested_plan = analysis / 'fill_plan.json'
            nested_plan.write_bytes(plan_file.read_bytes())
            with mock.patch.object(flow, 'resolve_source', side_effect=RuntimeError('gate passed')):
                with self.assertRaisesRegex(RuntimeError, 'gate passed'):
                    flow.build(nested_plan, first / 'out.pptx')
            pending = self.folder / 'pending'
            selection.prepare(pending)
            with self.assertRaises(ValueError):
                flow.require_confirmed({'template_id': first_id}, project=pending)
            nested = pending / 'analysis'
            nested.mkdir()
            with self.assertRaises(ValueError):
                flow.require_confirmed({'template_id': second_id}, project=nested)

    def test_updater_refuses_skill_copied_into_another_repository(self):
        result = subprocess.CompletedProcess([], 0, str(self.folder), '')
        with mock.patch.object(update_repo, 'run_command', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'checkout'):
                update_repo.ensure_repository_checkout()

    def test_updater_refuses_copied_source_layout_in_another_repository(self):
        result = subprocess.CompletedProcess([], 0, str(self.folder), '')
        with mock.patch.object(update_repo, 'REPO_ROOT', self.folder), \
                mock.patch.object(update_repo, 'run_command', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'checkout'):
                update_repo.ensure_repository_checkout()

    def test_updater_syncs_changed_core_dependencies(self):
        args = mock.Mock(skip_pip=False, full=False)
        result = subprocess.CompletedProcess([], 0, '', '')
        core = update_repo.SKILL_DIR / 'requirements-core.txt'
        with mock.patch.object(update_repo, 'parse_args', return_value=args), \
                mock.patch.object(update_repo, 'ensure_git_available'), \
                mock.patch.object(update_repo, 'ensure_repository_checkout', create=True), \
                mock.patch.object(update_repo, 'ensure_clean_tracked_worktree'), \
                mock.patch.object(update_repo, 'get_head_revision', side_effect=['before', 'after']), \
                mock.patch.object(update_repo, 'file_digest', side_effect=['old', 'new']), \
                mock.patch.object(update_repo, 'run_command', return_value=result), \
                mock.patch.object(update_repo, 'sync_python_dependencies') as sync:
            self.assertEqual(update_repo.main(), 0)
        sync.assert_called_once_with(core)

    def test_updater_retries_dependency_sync_after_pip_failure(self):
        args = mock.Mock(skip_pip=False, full=False)
        result = subprocess.CompletedProcess([], 0, '', '')
        with mock.patch.object(update_repo, 'parse_args', return_value=args), \
                mock.patch.object(update_repo, 'ensure_git_available'), \
                mock.patch.object(update_repo, 'ensure_repository_checkout'), \
                mock.patch.object(update_repo, 'ensure_clean_tracked_worktree'), \
                mock.patch.object(update_repo, 'get_head_revision', side_effect=['old', 'new', 'new', 'new']), \
                mock.patch.object(update_repo, 'file_digest', side_effect=['old', 'new', 'new', 'new']), \
                mock.patch.object(update_repo, 'run_command', return_value=result), \
                mock.patch.object(update_repo, 'sync_python_dependencies',
                                  side_effect=[subprocess.CalledProcessError(1, 'pip'), None]) as sync:
            self.assertEqual(update_repo.main(), 1)
            self.assertEqual(update_repo.main(), 0)
        self.assertEqual(sync.call_count, 2)

    def test_full_requirements_include_core(self):
        text = (update_repo.SKILL_DIR / 'requirements.txt').read_text(encoding='utf-8')
        self.assertIn('-r requirements-core.txt', text.splitlines())


if __name__ == '__main__':
    unittest.main()
