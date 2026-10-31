"""The optional maintainer renderer must stop before touching active Office."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


def load_renderer():
    path = Path(__file__).resolve().parents[1] / "scripts/render_showcase.py"
    spec = importlib.util.spec_from_file_location("render_showcase", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ShowcaseSafetyTests(unittest.TestCase):
    def test_existing_powerpoint_is_never_attached_to(self):
        renderer = load_renderer()
        result = subprocess.CompletedProcess([], 0, stdout=b'"POWERPNT.EXE","1234"')
        with patch.object(renderer.os, "name", "nt"), \
                patch.object(renderer.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                patch.object(renderer.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "PowerPoint is running"):
                renderer.main()

    def test_failed_process_detection_stops_rendering(self):
        renderer = load_renderer()
        with patch.object(renderer.os, "name", "nt"), \
                patch.object(renderer.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                patch.object(renderer.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "tasklist")):
            with self.assertRaises(subprocess.CalledProcessError):
                renderer.main()
