"""Install a project-scoped skill and print a short usage guide."""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
AGENT_DIRECTORIES = {
    'codex': '.agents',
    'claude-code': '.claude',
    'cursor': '.cursor',
    'github-copilot': '.github',
    'gemini-cli': '.gemini',
}


def _ignore_local_files(directory: str, names: list[str]) -> set[str]:
    ignored = set(shutil.ignore_patterns(
        '__pycache__', '*.pyc', '*.local.json', 'path_status.json',
        '.env', '.env.*', '.git', '.venv', 'venv', '.cache')(directory, names))
    ignored.discard('.env.example')
    return ignored


def _remove_readonly(function, path, error_info):
    if not isinstance(error_info[1], PermissionError):
        raise error_info[1]
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    function(path)


def install(project: Path, agent: str) -> Path:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise NotADirectoryError(f'Project directory does not exist: {project}')
    if project == Path.home().resolve():
        raise ValueError('Choose a project instead of the user home directory. Use your skill manager for shared skills.')
    if project.is_relative_to(SKILL_DIR.resolve()):
        raise ValueError('Choose a project outside the source skill directory.')
    destination = project / AGENT_DIRECTORIES[agent] / 'skills/xmu-ppt'
    if not destination.resolve().is_relative_to(project):
        raise ValueError('Skill directory resolves outside the project. Use your skill manager.')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f'Existing skill. Back up and compare before reinstalling: {destination}')
    if not all((SKILL_DIR / name).is_file() for name in ('SKILL.md', 'GETTING_STARTED.md')):
        raise RuntimeError('Source skill is incomplete. Download the entire skill directory.')

    with tempfile.TemporaryDirectory(prefix='.xmu-ppt-install-', dir=project) as temporary:
        staged = Path(temporary) / 'xmu-ppt'
        shutil.copytree(SKILL_DIR, staged, ignore=_ignore_local_files)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir()
        try:
            for item in staged.iterdir():
                if item.name != 'SKILL.md':
                    item.rename(destination / item.name)
            # Publish the discovery entry only after all supporting files exist.
            (staged / 'SKILL.md').rename(destination / 'SKILL.md')
        except BaseException:
            shutil.rmtree(destination, onerror=_remove_readonly)
            raise
    return destination


def show_guide(skill_dir: Path, language: str = 'zh') -> None:
    if language == 'en':
        print('''Getting started with xmu-ppt
1. Describe your topic, audience, slide count and source material to your agent.
2. Confirm the content brief, choose a template, then receive an editable PPTX.
3. Have your own templates? Attach the PPTX files and say:
   "I have permission to use these templates. Add all of them to My Templates,
   then list their U identifiers, names, page counts and any failed imports."
4. The agent checks Python dependencies. requirements-core.txt is inside this skill.
   Restart or reload your agent and check skill discovery. Trust the workspace when required.''')
    else:
        print('''xmu-ppt 简单使用
1. 直接告诉 Agent 主题、听众、页数，并提供材料。
2. 确认内容策划案，选择模板，随后接收可编辑的 PPTX。
3. 有自己的模板？上传一批 PPTX，并发送：
   “这些模板我有权使用，请逐份入库并加入我的模板库，列出 U 编号、名称、页数和失败项。”
4. Agent 会先检查 Python 依赖，核心依赖文件为本技能中的 requirements-core.txt。
   重新打开或重载 Agent 后核对技能发现，需要时完成工作区信任确认。''')
    print(f'GETTING_STARTED.md  {skill_dir / "GETTING_STARTED.md"}')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=AGENT_DIRECTORIES)
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='Existing target project directory')
    parser.add_argument('--guide', action='store_true', help='Show usage for this skill without installing')
    parser.add_argument('--lang', choices=['zh', 'en'], default='zh')
    args = parser.parse_args(argv)
    if args.guide:
        show_guide(SKILL_DIR, args.lang)
        return 0
    if not args.agent:
        parser.error('--agent is required when installing')
    try:
        destination = install(args.project, args.agent)
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    message = 'Skill files installed' if args.lang == 'en' else '技能文件已安装'
    print(f'{message}  {destination}\n')
    show_guide(destination, args.lang)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
