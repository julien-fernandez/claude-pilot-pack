#!/usr/bin/env python3
"""Claude Code Stop hook: block a turn that announces "Q<n> — …" when Q<n> is absent from today's registry."""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

PILOT_DIR = Path(os.environ.get("PILOT_DIR", Path.home() / ".local" / "state" / "claude-pilot"))
ANNOUNCE = re.compile(r"^\s*(?:[-*>]\s+|\d+[.)]\s+|#+\s+)*\**\s*(Q\d+(?:\.\d+)*)\b\**\s*(?:—|–|-\s+(?!Q\d))", re.M)
FENCE = re.compile(r"^\s*```.*?^\s*```", re.M | re.S)


def is_prompt(entry):
    if entry.get("type") != "user" or entry.get("isSidechain"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    return isinstance(content, list) and any(c.get("type") == "text" for c in content)


def current_turn_text(transcript):
    texts = []
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if is_prompt(entry):
            texts = []
        elif entry.get("type") == "assistant" and not entry.get("isSidechain"):
            for c in (entry.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "text":
                    texts.append(c.get("text", ""))
    return "\n".join(texts)


def registered(day):
    path = PILOT_DIR / "questions" / f"{day}.jsonl"
    if not path.exists():
        return set()
    numbers = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            numbers.add(json.loads(line)["q"])
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return numbers


def main():
    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active") or not payload.get("transcript_path"):
        return
    announced = list(dict.fromkeys(ANNOUNCE.findall(FENCE.sub("", current_turn_text(payload["transcript_path"])))))
    known = registered(dt.date.today().isoformat())
    unknown = [q for q in announced if q not in known]
    if unknown:
        print(json.dumps({
            "decision": "block",
            "reason": (f"{', '.join(unknown)} announced but absent from today's registry. "
                       "Register each with q new --source <slug> \"<question>\" and use the number it prints."),
        }))


if __name__ == "__main__":
    main()
