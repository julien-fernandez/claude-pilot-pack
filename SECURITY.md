# Security policy

## Reporting a vulnerability

Please report security issues privately, through GitHub security advisories on this repository
("Security" tab, "Report a vulnerability"). Do not open a public issue for them.

## What the pack does with data

The pack stores everything locally, in `PILOT_DIR` (default `~/.local/state/claude-pilot`) and in `~/.claude`.
Its scripts and hook open no network connection and send nothing anywhere. Network traffic only comes from
Claude Code itself, which the `sub-session` script starts with `claude --bg`.
