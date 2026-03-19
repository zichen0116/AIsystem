import os
import subprocess
import sys
from pathlib import Path
import unittest


class CoreImportTests(unittest.TestCase):
    def test_importing_database_module_does_not_require_valid_debug_setting(self):
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["DEBUG"] = "release"

        result = subprocess.run(
            [sys.executable, "-c", "from app.core.database import Base; print(Base.__name__)"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Base", result.stdout)


if __name__ == "__main__":
    unittest.main()
