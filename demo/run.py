#!/usr/bin/env python3
"""Offline demo of claude-pilot-pack.

Plays a short pilot scenario with the real scripts in a throwaway PILOT_DIR, with a stub in place of the
claude binary, and renders every command with its real output as a static HTML page.
"""
import argparse
import html
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = {
    "q": ROOT / "skills" / "question-registry" / "scripts" / "q",
    "sub-session": ROOT / "skills" / "sub-session" / "scripts" / "sub-session",
    "q-registered.py": ROOT / "hooks" / "q-registered.py",
}

STUB_CLAUDE = """#!/usr/bin/env python3
import hashlib, sys
name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "session"
print("Started background session " + hashlib.sha1(name.encode()).hexdigest()[:8] + " (" + name + ")")
"""

BRIEFS = {
    "invoice-parser": """# Mission: parse supplier invoices

Goal: `parse.py` turns the 40 sample PDFs in `samples/` into one CSV row each, totals matching
Budget: 2 h, 200K tokens; stop and write your state at the ceiling
Forbidden: publish, merge, delete samples, contact anyone
Proof: test output of `python3 -m unittest`, the CSV diff
State file: state/invoice-parser.md
""",
    "blog-redesign": """# Mission: redesign the blog index

Goal: the blog index renders the 12 latest posts as cards, light and dark, no layout shift
Budget: 1 h 30, 150K tokens
Forbidden: deploy, change post content, add a tracking script
Proof: before/after screenshots, build log
State file: state/blog-redesign.md
""",
}

REPORT = """## Produced
`parse.py` and `tests/test_parse.py`; 40 of 40 sample invoices parsed into `out/invoices.csv`.
## Verified
`python3 -m unittest`: 12 tests OK; CSV totals equal the PDF totals for all 40 samples.
## Not verified
Invoices in a currency other than EUR (none in the samples).
## Cost
1 h 10, about 120K tokens.
## Lessons
Two suppliers print the VAT line after the total; the parser reads the whole page before summing.
Closing: closable after Q1 is applied (date format chosen: ISO 8601)
"""

BAD_REPORT = """## Produced
`parse.py`, done.
Closing: closable now
"""


class Demo:
    def __init__(self, work):
        self.work = work
        self.pilot_dir = work / "state"
        self.steps = []
        bin_dir = work / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "claude"
        stub.write_text(STUB_CLAUDE, encoding="utf-8")
        stub.chmod(0o755)
        base = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_BIN", "PILOT_NAME", "PILOT_DIR")}
        self.env = {**base, "PILOT_DIR": str(self.pilot_dir), "CLAUDE_BIN": str(stub), "PILOT_NAME": "pilot"}
        self.replacements = [(str(self.pilot_dir), "$PILOT_DIR"), (str(work), "~/demo")]

    def hide(self, text):
        for old, new in self.replacements:
            text = text.replace(old, new)
        return text

    def section(self, title, note):
        self.steps.append({"title": title, "note": note, "runs": []})

    def run(self, name, *args, stdin=None, shown_stdin=None, cwd=None):
        result = subprocess.run([sys.executable, str(SCRIPTS[name]), *args], input=stdin,
                                capture_output=True, text=True, env=self.env, cwd=cwd or self.work)
        if name == "q-registered.py":
            command = f"python3 ~/.claude/hooks/q-registered.py < {shown_stdin}"
        else:
            command = " ".join([name, *(shlex.quote(a) for a in args)])
            if shown_stdin:
                command += f" <<'EOF'\n{shown_stdin.rstrip()}\nEOF"
        output = result.stdout + result.stderr
        self.steps[-1]["runs"].append({"command": self.hide(command), "output": self.hide(output),
                                       "code": result.returncode})
        return result

    def show_file(self, path):
        text = path.read_text(encoding="utf-8")
        self.steps[-1]["runs"].append({"command": f"cat {self.hide(str(path))}", "output": text, "code": 0})

    def transcript(self, name, prompt, text):
        lines = [{"type": "user", "message": {"role": "user", "content": prompt}},
                 {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}]
        path = self.work / name
        path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
        payload = json.dumps({"session_id": "demo", "transcript_path": str(path),
                              "hook_event_name": "Stop", "stop_hook_active": False})
        return payload, text

    def hook(self, label, prompt, text):
        payload, said = self.transcript(f"{label}.jsonl", prompt, text)
        self.steps[-1]["runs"].append({"command": f"# the session's last message ({label})", "output": said,
                                       "code": 0, "quote": True})
        result = self.run("q-registered.py", stdin=payload, shown_stdin=f"stop-payload-{label}.json")
        if not result.stdout.strip() and not result.returncode:
            self.steps[-1]["runs"][-1]["output"] = "(no output: the turn may end)\n"
        return result

    def play(self):
        repos = {}
        for slug, brief in BRIEFS.items():
            repo = self.work / "repos" / slug
            repo.mkdir(parents=True)
            (self.work / "briefs").mkdir(exist_ok=True)
            (self.work / "briefs" / f"{slug}.md").write_text(brief, encoding="utf-8")
            repos[slug] = repo

        self.section("1. The pilot writes a brief per mission",
                     "Each brief carries the five mandatory lines: Goal, Budget, Forbidden, Proof, State file.")
        self.show_file(self.work / "briefs" / "invoice-parser.md")

        self.section("2. The pilot launches two sub-sessions",
                     "A brief missing a mandatory line is refused before anything starts. "
                     "Here claude --bg is a local stub: no session is really started and no token is spent.")
        incomplete = self.work / "briefs" / "draft.md"
        incomplete.write_text("# Mission: draft\n\nGoal: something useful\n", encoding="utf-8")
        self.run("sub-session", "launch", "draft", "repos/blog-redesign", "briefs/draft.md")
        for slug in BRIEFS:
            self.run("sub-session", "launch", slug, f"repos/{slug}", f"briefs/{slug}.md")
        self.run("sub-session", "list")

        self.section("3. Sub-sessions register their questions",
                     "Numbers come from one shared daily registry, so two sessions never both announce the same Q.")
        self.run("q", "new", "--source", "invoice-parser", "--reco", "ISO 8601",
                 "Which date format for the CSV: ISO 8601 or DD/MM/YYYY?")
        self.run("q", "new", "--source", "blog-redesign", "--reco", "3 columns",
                 "Cards grid on desktop: 3 or 4 columns?")
        self.run("q", "new", "--source", "blog-redesign", "--parent", "Q2", "--reco", "yes",
                 "Keep the excerpt under the title on mobile?")

        self.section("4. The Stop hook guards the numbering",
                     "A turn that announces a question number absent from today's registry is blocked; "
                     "a registered one goes through.")
        self.hook("unregistered", "Go on with the grid.",
                  "Grid done on desktop.\n\n**Q3 —** Should the cards show the reading time? Recommended: yes")
        self.hook("registered", "Go on with the grid.",
                  "Grid done on desktop.\n\n**Q2.1 —** Keep the excerpt under the title on mobile? Recommended: yes")

        self.section("5. The pilot answers in one batch",
                     "The human answers the open questions in the pilot's window; the pilot records each answer.")
        self.run("q", "list", "--open")
        self.run("q", "answer", "Q1", "ISO 8601")
        self.run("q", "answer", "Q2.1", "yes, two lines at most")

        self.section("6. A sub-session stores its report",
                     "The five sections and the Closing line are enforced: an incomplete report is refused.")
        self.run("sub-session", "report", "invoice-parser", stdin=BAD_REPORT, shown_stdin=BAD_REPORT)
        self.run("sub-session", "report", "invoice-parser", stdin=REPORT, shown_stdin=REPORT)
        self.run("sub-session", "list")

        self.section("7. What is still open",
                     "Only Q2 waits for the human; the full list keeps the answers.")
        self.run("q", "list", "--open")
        self.run("q", "list")


CSS = """
:root { color-scheme: light dark; --bg: #f7f7f5; --fg: #1d1d1b; --muted: #5d5d58; --term-bg: #ffffff;
  --term-fg: #1d1d1b; --border: #d8d8d2; --prompt: #1b6e3a; --err: #b42318; --quote: #f0efe9; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161615; --fg: #ececea; --muted: #a3a39d; --term-bg: #0e0e0d; --term-fg: #e4e4e0;
    --border: #33332f; --prompt: #6fd08f; --err: #ff8a7a; --quote: #20201e; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 920px; margin: 0 auto; padding: 32px 16px 64px; }
h1 { font-size: 1.7rem; margin: 0 0 4px; }
h2 { font-size: 1.15rem; margin: 36px 0 4px; }
p { margin: 0 0 12px; color: var(--muted); }
.term { background: var(--term-bg); color: var(--term-fg); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 14px; overflow-x: auto; }
pre { margin: 0; font: 13.5px/1.5 ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  white-space: pre-wrap; word-break: break-word; }
.cmd { color: var(--prompt); }
.cmd + pre { margin-top: 2px; }
.run + .run { margin-top: 10px; }
.quote { background: var(--quote); border-left: 3px solid var(--border); padding: 6px 10px; border-radius: 4px; }
.code { color: var(--err); font-size: 12.5px; }
code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.92em; }
footer { margin-top: 40px; font-size: 0.9rem; color: var(--muted); }
"""


def render(steps):
    parts = []
    for step in steps:
        runs = []
        for run in step["runs"]:
            command = html.escape(run["command"])
            output = html.escape(run["output"].rstrip("\n"))
            if run.get("quote"):
                runs.append(f'<div class="run"><pre class="cmd">{command}</pre>'
                            f'<pre class="quote">{output}</pre></div>')
                continue
            code = f'<div class="code">exit code {run["code"]}</div>' if run["code"] else ""
            body = f"<pre>{output}</pre>" if output else ""
            runs.append(f'<div class="run"><pre class="cmd">$ {command}</pre>{body}{code}</div>')
        note = html.escape(step["note"])
        parts.append(f'<section><h2>{html.escape(step["title"])}</h2><p>{note}</p>'
                     f'<div class="term">{"".join(runs)}</div></section>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>claude-pilot-pack — demo</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>claude-pilot-pack — demo</h1>
<p>A pilot session, two sub-sessions, one question registry and a Stop hook, played offline.
Every command below ran for real against the pack's scripts; only <code>claude --bg</code> is a stub.</p>
{"".join(parts)}
<footer>Recorded by <code>demo/run.py</code> in a throwaway <code>PILOT_DIR</code>.
Mission names are fictional.</footer>
</main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Play the offline demo and write it as an HTML page.")
    parser.add_argument("--out", default="out", help="output directory, or an .html file path")
    args = parser.parse_args()
    out = Path(args.out)
    if out.suffix != ".html":
        out = out / "index.html"
    with tempfile.TemporaryDirectory(prefix="pilot-demo-") as tmp:
        demo = Demo(Path(tmp))
        demo.play()
        page = render(demo.steps)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
