#!/usr/bin/env python3
"""Update the repository and sync Python dependencies when needed.

Usage:
    python3 skills/xmu-ppt/scripts/update_repo.py
    python3 skills/xmu-ppt/scripts/update_repo.py --skip-pip
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TOOLS_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent
REQUIREMENTS_FILE = SKILL_DIR / "requirements.txt"
CORE_REQUIREMENTS_FILE = SKILL_DIR / "requirements-core.txt"
DEPENDENCY_STATE_DIR = REPO_ROOT / ".cache" / "dependency-updates"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Pull the latest repository changes and sync Python dependencies "
            "when the selected requirements change (core dependencies by default)."
        )
    )
    parser.add_argument(
        "--skip-pip",
        action="store_true",
        help="Skip Python dependency sync even if requirements changed.",
    )
    parser.add_argument("--full", action="store_true",
                        help="Sync optional dependencies from requirements.txt as well.")
    return parser.parse_args()


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def file_digest(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_git_available() -> None:
    if shutil.which("git") is None:
        raise RuntimeError("Missing executable: git")


def ensure_repository_checkout() -> None:
    result = run_command(["git", "rev-parse", "--show-toplevel"], check=False)
    if (result.returncode != 0
            or Path(result.stdout.strip()).resolve() != REPO_ROOT.resolve()
            or not (REPO_ROOT / "scripts/pack_release.py").is_file()):
        raise RuntimeError(
            "Run this updater from the original xmu-ppt Git checkout. "
            "For a copied skill or ZIP, update through its installer or download a new archive."
        )


def ensure_clean_tracked_worktree() -> None:
    status = run_command(["git", "status", "--porcelain", "--untracked-files=no"], check=False)
    if status.returncode != 0:
        details = (status.stderr or status.stdout or "").strip()
        raise RuntimeError(details or "Unable to inspect git status.")

    if status.stdout.strip():
        raise RuntimeError(
            "Tracked local changes detected. Please commit or stash them before running the update command."
        )


def get_head_revision() -> str:
    result = run_command(["git", "rev-parse", "HEAD"])
    return result.stdout.strip()


def sync_python_dependencies(requirements_file: Path = REQUIREMENTS_FILE) -> None:
    if not requirements_file.exists():
        raise RuntimeError(f"Missing dependency file: {requirements_file.name}")

    print(f"Syncing Python dependencies from {requirements_file.name}...")
    result = run_command([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())


def main() -> int:
    args = parse_args()

    try:
        ensure_git_available()
        ensure_repository_checkout()
        ensure_clean_tracked_worktree()

        before_head = get_head_revision()
        requirements_file = REQUIREMENTS_FILE if args.full else CORE_REQUIREMENTS_FILE
        watched = [CORE_REQUIREMENTS_FILE, REQUIREMENTS_FILE] if args.full else [CORE_REQUIREMENTS_FILE]
        before_requirements = [file_digest(path) for path in watched]

        print(f"Repository: {REPO_ROOT}")
        pull_result = run_command(["git", "pull", "--ff-only"])
        if pull_result.stdout.strip():
            print(pull_result.stdout.strip())
        if pull_result.stderr.strip():
            print(pull_result.stderr.strip())

        after_head = get_head_revision()
        after_requirements = [file_digest(path) for path in watched]
        signature = hashlib.sha256(repr((sys.executable, after_requirements)).encode("utf-8")).hexdigest()
        state_file = DEPENDENCY_STATE_DIR / f"{requirements_file.stem}.sha256"
        installed_signature = state_file.read_text(encoding="utf-8").strip() if state_file.exists() else None

        if before_head == after_head:
            print("Repository is already up to date.")
        else:
            print(f"Updated from {before_head[:7]} to {after_head[:7]}.")

        if args.skip_pip:
            print("Skipped Python dependency sync (--skip-pip).")
        elif before_requirements != after_requirements or installed_signature != signature:
            sync_python_dependencies(requirements_file)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(signature + "\n", encoding="utf-8")
        else:
            print("Selected requirements unchanged. Skipping Python dependency sync.")

        print("Note: system dependencies such as Node.js and Pandoc still need to be installed manually.")
        return 0
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        print(details or "Command failed.", file=sys.stderr)
        return exc.returncode or 1
    except (RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
