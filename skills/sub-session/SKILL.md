---
name: sub-session
description: Launch and follow a background Claude Code sub-session from a validated brief — fixed name, launch registry, standing instructions (never ask the human, register questions, keep a state file), and a final report whose five sections are enforced. Use when the pilot delegates a mission longer than ~30 minutes, "launch a sub-session", "delegate this", "what are my sub-sessions doing", or when a sub-session stores its final report.
---

# Sub-sessions

The pilot delegates each mission over ~30 minutes to its own background session. Shorter work stays in the
pilot or goes to a sub-agent.

## Launch

`sub-session` is on the PATH (set-up step 2); run it directly, without a `PILOT_DIR=…` prefix.

1. Copy `templates/brief.md` and fill it. These lines are mandatory (a `Field:` line or a `## Field` heading):
   `Goal`, `Budget`, `Forbidden`, `Proof`, `State file`.
2. Create the state file from `templates/state-file.md`.
3. Launch:

   ```bash
   sub-session launch <slug> <repo-dir> <brief.md>
   ```

   The launcher refuses a brief missing a mandatory line, appends the standing instructions below, runs
   `claude --bg --name <slug>` from `<repo-dir>`, and writes a line to the launch registry.
4. Reach it at once with `SendMessage({to: "<slug>"})`. Watch it with `claude attach <slug>` or
   `claude logs <slug>`; `claude agents` lists background sessions.

## Standing instructions (appended to every brief)

- Never ask the human anything. Register each decision with `q new --source <slug> --reco "<reco>" "<question>"`,
  send it to `pilot` by SendMessage (number, one line on what is done so far, options, recommendation),
  then continue with the rest.
- Update the state file at every step: what is done with its proof, next step, cost so far.
- Stop at the budget ceiling after writing the state file.
- End with `sub-session report <slug>` (below), then a summary of 8 lines at most to `pilot` by SendMessage.

## Report

```bash
sub-session report <slug> <<'EOF'
## Produced
## Verified
## Not verified
## Cost
## Lessons
Closing: closable now | closable after <condition> | not closable: <what is left>
EOF
```

The command refuses a report missing a section or the `Closing:` line. "Not verified" is mandatory on
purpose: "done" proves nothing without it.

Never write the report file or the launch registry by hand: the command checks the sections and the slug.

## Follow

`sub-session list` shows today's launches and which ones have stored a report.

## Configuration

| Variable | Default | Use |
|---|---|---|
| `PILOT_DIR` | `~/.local/state/claude-pilot` | launch registry (`sub-sessions.tsv`) and reports (`reports/`) |
| `CLAUDE_BIN` | `claude` from `PATH` | the Claude Code executable |
| `PILOT_NAME` | `pilot` | the name sub-sessions send their messages to |
