# AGENTS.md — install, test and demo claude-pilot-pack

Instructions for a coding agent. Run every command from the root of this repository. The pack is Python 3.10+
standard library only: no virtual environment, no `pip install`, no network access needed.

## 1. Check the prerequisites

```bash
python3 --version   # 3.10 or later
git --version
```

## 2. Install (optional: into a throwaway HOME)

To try the install without touching the real home directory, first run:

```bash
export HOME=$(mktemp -d)
```

Then install exactly as the README set-up does:

```bash
mkdir -p ~/.claude/skills ~/.local/bin ~/.claude/hooks
cp -r skills/* ~/.claude/skills/
ln -sf ~/.claude/skills/sub-session/scripts/sub-session ~/.local/bin/sub-session
ln -sf ~/.claude/skills/question-registry/scripts/q ~/.local/bin/q
cp hooks/q-registered.py ~/.claude/hooks/
export PATH="$HOME/.local/bin:$PATH"
```

Declare the Stop hook in `~/.claude/settings.json` (create the file if it does not exist; merge the `hooks`
block into it if it does):

```json
{ "hooks": { "Stop": [ { "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/q-registered.py" } ] } ] } }
```

Check the install:

```bash
PILOT_DIR=$(mktemp -d) q new --source test "Does the registry work?"
```

Expected output: one line, `Q1`.

## 3. Run the tests

```bash
python3 -m unittest discover -s tests
```

Expected: the last lines are `Ran 23 tests in …` and `OK`. The tests use a fake `claude` binary: they start no
real session and spend no tokens.

## 4. Run the demo locally

```bash
python3 demo/run.py --out out
```

Expected: it prints `out/index.html` and writes that page. The page, titled "claude-pilot-pack — demo", shows each
command and its real output: two sub-sessions launched from briefs, questions `Q1`, `Q2`, `Q2.1` registered, the
Stop hook blocking a turn that announces the unregistered `Q3`, answers recorded, a report refused then stored, and
the open list ending with `Q2` only. `--out` takes a directory (the page is written as `index.html` inside it) or
a path ending in `.html`.

## 5. Run the tests and the demo in Docker

```bash
docker build --target test -t claude-pilot-pack:test . && docker run --rm --network none claude-pilot-pack:test
```

Expected: `Ran 23 tests in …` then `OK`.

```bash
mkdir -p out && docker build -t claude-pilot-pack . && docker run --rm -v "$PWD/out:/out" claude-pilot-pack
```

Expected: it prints `/out/index.html`, and `out/index.html` exists on the host. The container runs as uid 1000;
if the host `out/` folder belongs to another uid, make it writable first (`chmod 777 out`).

## 6. Real use

The real use needs Claude Code with background sessions (`claude --bg`, `claude agents`) and SendMessage between
sessions. The demo and the tests replace `claude` with a stub (`CLAUDE_BIN` in the demo, a fake binary on `PATH`
in the tests), so neither needs Claude Code nor an API key. See the README for the pilot set-up.

## Rules for changes

- Keep the scripts standard library only, Python 3.10+.
- Run `python3 -m unittest discover -s tests` and `python3 demo/run.py --out out` before handing back.
- Do not commit `out/` or `__pycache__/`.
