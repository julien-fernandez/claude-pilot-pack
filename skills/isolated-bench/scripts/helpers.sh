# Helpers for "script" cases (loaded through BASH_ENV by play.py).
tr_() { # tr_ "<assistant text of the current turn>" ["<text of an earlier turn>"] -> writes tr.jsonl
python3 - "$@" <<'PY'
import json, sys
lines = []
if len(sys.argv) > 2:
    lines += [{"type": "user", "message": {"content": "earlier"}},
              {"type": "assistant", "message": {"content": [{"type": "text", "text": sys.argv[2]}]}}]
lines += [{"type": "user", "message": {"content": "go"}},
          {"type": "assistant", "message": {"content": [{"type": "text", "text": sys.argv[1]}]}}]
open("tr.jsonl", "w").write("\n".join(json.dumps(l) for l in lines) + "\n")
PY
}
hook_() { echo "{\"transcript_path\": \"$PWD/tr.jsonl\"${1:+, $1}}" | python3 ~/.claude/hooks/q-registered.py; }
brief_() { # brief_ <file> <goal>: a complete brief
  printf 'Goal: %s\nBudget: 5 minutes, 20K tokens.\nForbidden: publishing, network, anything outside %s.\nProof: the files named in the goal.\nState file: %s/state.md\n' "$2" "$PWD" "$PWD" > "$1"; }
stub_() { printf '#!/bin/sh\necho "backgrounded · stub · $3"\necho "$@" > "%s/stub-args"\n' "$PWD" > "$PWD/claude-stub"; chmod +x "$PWD/claude-stub"; export CLAUDE_BIN="$PWD/claude-stub"; }
trust_() { python3 - "${1:-$PWD}" <<'PY'
import json, pathlib, sys
c = pathlib.Path.home() / ".claude.json"; d = json.loads(c.read_text())
d.setdefault("projects", {}).setdefault(sys.argv[1], {})["hasTrustDialogAccepted"] = True
c.write_text(json.dumps(d))
PY
}
wait_() { # wait_ <seconds> <command>: retry the command until the deadline
  local end=$((SECONDS + $1)); shift
  until eval "$@"; do [ $SECONDS -ge $end ] && return 1; sleep 5; done; }
