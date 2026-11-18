import json
import os
from pathlib import Path

from helpers import PilotCase, SUB

FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_CLAUDE_LOG"], "a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
print("Started background session 1234abcd")
"""

GOOD_BRIEF = """# Mission: tidy the docs

Goal: the README lists every script
Budget: 1 h, 50K tokens
Forbidden: publish, merge
Proof: diff of README.md
State file: state/tidy-docs.md
"""


class SubSession(PilotCase):
    def setUp(self):
        super().setUp()
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        self.log = self.tmp / "claude-calls.jsonl"
        self.env = {**self.env, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_CLAUDE_LOG": str(self.log)}
        self.repo = self.tmp / "repo"
        self.repo.mkdir()

    def brief(self, text):
        path = self.tmp / "brief.md"
        path.write_text(text)
        return str(path)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def sub(self, *args, **kw):
        return self.run_cmd(SUB, *args, **kw)

    def test_valid_brief_launches_a_named_background_session_in_the_repo(self):
        result = self.sub("launch", "tidy-docs", str(self.repo), self.brief(GOOD_BRIEF))
        self.assertEqual(result.returncode, 0, result.stderr)
        [call] = self.calls()
        self.assertEqual(Path(call["cwd"]).resolve(), self.repo.resolve())
        argv = call["argv"]
        self.assertIn("--bg", argv)
        self.assertEqual(argv[argv.index("--name") + 1], "tidy-docs")
        prompt = argv[-1]
        self.assertIn("the README lists every script", prompt)
        self.assertIn("q new --source tidy-docs", prompt)
        self.assertIn("sub-session report tidy-docs", prompt)
        self.assertIn('"pilot"', prompt)

    def test_brief_missing_mandatory_lines_is_refused_without_launching(self):
        brief = "# Mission\n\n## Goal\nship it\n\nBudget: 1 h\n"
        result = self.sub("launch", "loose", str(self.repo), self.brief(brief))
        self.assertNotEqual(result.returncode, 0)
        for field in ("Forbidden", "Proof", "State file"):
            self.assertIn(field, result.stderr)
        self.assertNotIn("Goal,", result.stderr)
        self.assertEqual(self.calls(), [])

    FULL_REPORT = """## Produced
README updated.
## Verified
Tests pass.
## Not verified
Install on macOS.
## Cost
40 min, 30K tokens.
## Lessons
None.
Closing: closable now
"""

    def test_incomplete_report_is_refused_and_complete_one_is_stored(self):
        partial = self.FULL_REPORT.replace("## Not verified\nInstall on macOS.\n", "")
        refused = self.sub("report", "tidy-docs", stdin=partial)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("Not verified", refused.stderr)
        no_closing = self.FULL_REPORT.replace("Closing: closable now\n", "")
        self.assertNotEqual(self.sub("report", "tidy-docs", stdin=no_closing).returncode, 0)
        stored = self.sub("report", "tidy-docs", stdin=self.FULL_REPORT)
        self.assertEqual(stored.returncode, 0, stored.stderr)
        reports = list((self.pilot_dir / "reports").glob("*tidy-docs*.md"))
        self.assertEqual(len(reports), 1)
        self.assertIn("Install on macOS.", reports[0].read_text())

    def test_list_shows_launches_and_which_have_reported(self):
        self.sub("launch", "tidy-docs", str(self.repo), self.brief(GOOD_BRIEF))
        self.sub("launch", "fix-tests", str(self.repo), self.brief(GOOD_BRIEF))
        self.sub("report", "tidy-docs", stdin=self.FULL_REPORT)
        lines = self.sub("list").stdout.splitlines()
        tidy = next(l for l in lines if "tidy-docs" in l)
        fix = next(l for l in lines if "fix-tests" in l)
        self.assertIn("reported", tidy)
        self.assertNotIn("reported", fix)
        self.assertIn(str(self.repo), tidy)

    def test_unfilled_template_placeholders_count_as_missing(self):
        from helpers import ROOT
        template = (ROOT / "templates" / "brief.md").read_text()
        result = self.sub("launch", "raw", str(self.repo), self.brief(template))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Goal", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_skeleton_report_with_empty_sections_is_refused(self):
        skeleton = "## Produced\n## Verified\n## Not verified\n## Cost\n## Lessons\nClosing: closable now\n"
        result = self.sub("report", "tidy-docs", stdin=skeleton)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Produced", result.stderr)

    def test_bold_and_bulleted_brief_fields_are_accepted(self):
        brief = ("**Goal:** ship\n**Budget:** 1 h\n- Forbidden: publish\n- Proof: diff\n"
                 "* **State file:** state/x.md\n")
        result = self.sub("launch", "styled", str(self.repo), self.brief(brief))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unsafe_slugs_are_refused(self):
        for slug in ("../escape", "has\ttab", "Upper Case"):
            result = self.sub("report", slug, stdin=self.FULL_REPORT)
            self.assertNotEqual(result.returncode, 0, slug)
        self.assertFalse((self.pilot_dir / "reports").exists())
