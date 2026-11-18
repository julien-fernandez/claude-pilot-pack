import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "skills" / "question-registry" / "scripts" / "q"
SUB = ROOT / "skills" / "sub-session" / "scripts" / "sub-session"
HOOK = ROOT / "hooks" / "q-registered.py"


class PilotCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.pilot_dir = self.tmp / "pilot"
        base = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_BIN", "PILOT_NAME", "PILOT_DIR")}
        self.env = {**base, "PILOT_DIR": str(self.pilot_dir)}

    def tearDown(self):
        self._tmp.cleanup()

    def run_cmd(self, script, *args, stdin=None, env=None, cwd=None):
        return subprocess.run(
            ["python3", str(script), *args],
            input=stdin, capture_output=True, text=True,
            env=env or self.env, cwd=cwd,
        )

    def q(self, *args, **kw):
        return self.run_cmd(Q, *args, **kw)
