"""Project installation must finish with an actionable welcome message."""
import contextlib
import importlib.util
import io
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/xmu-ppt/scripts/install_skill.py'


class SkillInstallationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'Missing installation and welcome entry point')
        spec = importlib.util.spec_from_file_location('xmu_install_skill', SCRIPT)
        self.installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.installer)
        (ROOT / '.cache').mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / '.cache')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.source = self.folder / 'source'
        (self.source / 'scripts').mkdir(parents=True)
        (self.source / 'SKILL.md').write_text('name: xmu-ppt\n', encoding='utf-8')
        (self.source / 'GETTING_STARTED.md').write_text('使用教程\n', encoding='utf-8')
        (self.source / 'scripts/example.py').write_text('print(1)\n', encoding='utf-8')
        patcher = mock.patch.object(self.installer, 'SKILL_DIR', self.source)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_installs_complete_skill_for_each_project_host(self):
        locations = {'codex': '.agents', 'claude-code': '.claude', 'cursor': '.cursor',
                     'github-copilot': '.github', 'gemini-cli': '.gemini'}
        for agent, directory in locations.items():
            with self.subTest(agent=agent):
                project = self.folder / agent
                project.mkdir()
                target = self.installer.install(project, agent)
                self.assertEqual(target, project / directory / 'skills/xmu-ppt')
                self.assertEqual((target / 'SKILL.md').read_bytes(),
                                 (self.source / 'SKILL.md').read_bytes())
                self.assertTrue((target / 'GETTING_STARTED.md').is_file())
                self.assertTrue((target / 'scripts/example.py').is_file())

    def test_success_prints_usage_and_template_import_prompt(self):
        project = self.folder / 'project'
        project.mkdir()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = self.installer.main(['--agent', 'codex', '--project', str(project)])
        self.assertEqual(code, 0)
        for text in ('技能文件已安装', '简单使用', '模板', '入库', '有权使用',
                     '内容策划案', 'PPTX', 'requirements-core.txt', 'GETTING_STARTED.md'):
            self.assertIn(text, output.getvalue())

    def test_existing_skill_is_preserved_and_no_success_is_printed(self):
        project = self.folder / 'project'
        target = project / '.agents/skills/xmu-ppt'
        target.mkdir(parents=True)
        original = target / 'SKILL.md'
        original.write_text('existing user skill', encoding='utf-8')
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = self.installer.main(['--agent', 'codex', '--project', str(project)])
        self.assertEqual(code, 1)
        self.assertEqual(original.read_text(encoding='utf-8'), 'existing user skill')
        self.assertNotIn('技能文件已安装', output.getvalue())

    def test_copy_failure_leaves_no_discoverable_skill(self):
        project = self.folder / 'project'
        project.mkdir()
        with mock.patch.object(self.installer.shutil, 'copytree', side_effect=OSError('copy failed')):
            with self.assertRaises(OSError):
                self.installer.install(project, 'codex')
        self.assertFalse((project / '.agents/skills/xmu-ppt/SKILL.md').exists())
        self.assertEqual(list(project.glob('.xmu-ppt-install-*')), [])

    def test_guide_can_be_shown_without_installing(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.installer.main(['--guide']), 0)
        self.assertIn('简单使用', output.getvalue())
        self.assertNotIn('技能文件已安装', output.getvalue())

    def test_installation_inside_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside the source'):
            self.installer.install(self.source, 'codex')

    def test_publish_failure_removes_only_the_new_target(self):
        project = self.folder / 'project'
        project.mkdir()
        with mock.patch.object(Path, 'rename', side_effect=OSError('publish failed')):
            with self.assertRaises(OSError):
                self.installer.install(project, 'codex')
        self.assertFalse((project / '.agents/skills/xmu-ppt').exists())
        self.assertTrue((self.source / 'SKILL.md').is_file())

    def test_user_home_is_rejected_as_a_project(self):
        home = self.folder / 'home'
        home.mkdir()
        with mock.patch.object(Path, 'home', return_value=home):
            with self.assertRaisesRegex(ValueError, 'home directory'):
                self.installer.install(home, 'codex')

    def test_local_environment_files_are_excluded(self):
        for name in ('.env', '.env.local', '.env.production', '.env.example'):
            (self.source / name).write_text('local test fixture', encoding='utf-8')
        project = self.folder / 'project'
        project.mkdir()
        target = self.installer.install(project, 'codex')
        for name in ('.env', '.env.local', '.env.production'):
            self.assertFalse((target / name).exists(), name)
        self.assertTrue((target / '.env.example').is_file())

    @unittest.skipUnless(os.name == 'nt', 'Windows read-only file cleanup')
    def test_publish_failure_cleans_readonly_resources(self):
        readonly = self.source / 'scripts/readonly.py'
        readonly.write_text('pass\n', encoding='utf-8')
        readonly.chmod(stat.S_IREAD)
        self.addCleanup(readonly.chmod, stat.S_IREAD | stat.S_IWRITE)
        project = self.folder / 'project'
        project.mkdir()
        rename = Path.rename

        def fail_entry(path, target):
            if path.name == 'SKILL.md':
                raise OSError('publish failed')
            return rename(path, target)

        with mock.patch.object(Path, 'rename', new=fail_entry):
            with self.assertRaisesRegex(OSError, 'publish failed'):
                self.installer.install(project, 'codex')
        self.assertFalse((project / '.agents/skills/xmu-ppt').exists())

    def test_english_welcome_is_available(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.installer.main(['--guide', '--lang', 'en']), 0)
        self.assertIn('Getting started', output.getvalue())
        self.assertIn('templates', output.getvalue())


if __name__ == '__main__':
    unittest.main()
