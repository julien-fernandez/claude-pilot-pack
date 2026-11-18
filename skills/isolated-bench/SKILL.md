---
name: isolated-bench
description: Prove a repo, a pack of skills or a hook in a fresh, isolated container with the real Claude Code CLI — empty HOME, no mount of the owner's files, credentials mounted read-only at start and destroyed at the end — then play its use cases with `claude -p` and real `claude --bg` sessions. Use before publishing or handing over a pack, "test it in an isolated environment", "does the skill really trigger", "does the hook block", "does claude --bg really launch", or when tests only ran against a stub of claude.
---

# Isolated bench

Unit tests with a stub of `claude` prove the scripts. They do not prove that Claude Code loads the skill on the
user's words, that the hook fires on a real turn, or that `claude --bg` starts a session that does the work.
The bench does, in a container that knows nothing of your machine.

## Rules

- **Fresh container, fresh HOME.** Build from the repo's own install steps (its Dockerfile or README), add the
  Claude Code CLI at a pinned version. Mount nothing from your HOME except what the next rule allows.
- **Credentials never in an image, a commit, a log or a chat.** Mount the credentials file read-only at start
  (`-v ~/.claude/.credentials.json:/run/bench-creds/credentials.json:ro`); the entry script copies it into the
  container's HOME with mode 600. Destroy the container at the end (`docker rm -f`); started with `--rm`, its HOME
  goes with it. Never `docker commit` a running bench.
- **Narrow permissions, not bypass.** Write `permissions.allow` in the container's `settings.json` for the tools
  the cases need (`Bash(q:*)`, `Write`, `Skill`…). Do not run cases with `bypassPermissions`.
- **One working folder per case**, fresh, with its own state directory (here `PILOT_DIR`), so cases never see
  each other's data.
- **Stub where the case is not about it.** A case about the launcher's refusals uses a stub of `claude --bg`; a case
  about the launch uses the real one.

## Steps

1. Write the cases first (`use-cases` skill): `cases.jsonl` with `script`, `claude` and `nt` kinds.
2. Build: the repo's image (its install stage), then `FROM` it, add `curl git`, install Claude Code
   (`curl -fsSL https://claude.ai/install.sh | bash -s <version>`), copy the runner and the cases.
3. Start: `docker run -d --rm --name bench --cpus 4 --memory 4g -v <creds>:…:ro -v <results>:/out <image>`.
4. Smoke test: `docker exec bench claude -p "Reply PONG"`. Then one real `claude --bg` launch.
5. Play the first batch: `docker exec bench python3 /bench/play.py --lot 1` (`scripts/play.py`, copied into the image with the cases as `/bench/cases.jsonl`; shell helpers for `script` cases in `/bench/helpers.sh`, loaded through `BASH_ENV`). For `claude` cases the runner calls
   `claude -p <prompt> --output-format stream-json --verbose --include-hook-events --max-turns 10` and reads:
   - skills loaded: `tool_use` entries named `Skill` and their `skill` input;
   - hook decisions: `system` events of subtype `hook_response` whose stdout holds `"decision": "block"`;
   - cost and turns: the final `result` event.
   It keeps every trace as `traces/<id>.jsonl` and appends one line per case to `results.jsonl`.
6. Read every failure: a bench bug (fix the bench, replay) or a finding about the repo (write it down).
7. Destroy: delete the copied credentials, `docker rm -f bench`, remove the images if not reused.
8. Scan the results folder for secrets (gitleaks or equivalent) before committing it: traces quote the model's
   output, never the credentials, but check.

## Traps met

- **A fresh HOME is not isolation when you log in with a subscription.** The account's OAuth credentials bring
  its claude.ai connectors (mail, calendar, documents…) and the organisation's plugins into the container: a
  case asking "prepare my decisions" read the owner's calendar and mail instead of loading the skill. Before any
  case: `-e ENABLE_CLAUDEAI_MCP_SERVERS=false` on `docker run`, the same in `settings.json` `env` (background
  sessions read it), and `--strict-mcp-config --mcp-config '{"mcpServers": {}}'` on every `claude -p`. The runner
  (`scripts/play.py`) fails a case whose `init` event lists any `mcp__` tool and does not keep its trace. If it
  happened, shred the traces and destroy the container before replaying.
- A background session inherits the environment of Claude Code's background service, not the launcher's: a
  variable exported before `claude --bg` does not reach it. Put it in `settings.json` `env`.
- `claude --bg` refuses a folder never trusted: "Workspace not trusted. Run `claude` in <dir> once". A fresh user
  launching a sub-session into a repo never opened in Claude Code hits it. In the bench, set
  `projects["<dir>"].hasTrustDialogAccepted = true` in `~/.claude.json` for the cases that need a real launch, and
  keep one case without it to show the behaviour.
- `claude agents` needs a TTY: use `claude agents --json` from a script.
- Commands holding `$VARIABLES` can be denied in non-interactive mode ("A variable in this command can't be
  checked before it runs"); the model usually retries without them, at the cost of a turn.
- Shell heredocs and backquotes inside a case's command are expanded by the runner's shell: quote with `$'…'`.
- The session's model, not the bench, decides whether a skill loads: replay a failed trigger once before calling
  it a finding, and keep both traces.
