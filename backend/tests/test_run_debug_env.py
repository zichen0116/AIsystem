import os
import subprocess
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class RunDebugEnvTests(unittest.TestCase):
    def test_run_import_accepts_release_debug_env(self):
        env = os.environ.copy()
        env["DEBUG"] = "release"

        result = subprocess.run(
            [sys.executable, "-c", "import run; print(run.settings.DEBUG)"],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().endswith("False"))

    def test_run_import_accepts_development_debug_env(self):
        env = os.environ.copy()
        env["DEBUG"] = "development"

        result = subprocess.run(
            [sys.executable, "-c", "import run; print(run.settings.DEBUG)"],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().endswith("True"))


if __name__ == "__main__":
    unittest.main()
