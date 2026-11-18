---
name: question-registry
description: Number every question meant for the human through one daily registry (Q1, Q2… across all sessions, sub-questions Q4.1), record answers, list what is still open. Use whenever a session needs a decision from the human, when the pilot records an answer, "what is still open", "open questions", or when a Stop hook refuses an unregistered Q number.
---

# Question registry

One numbering per day for every session, so the human never sees two different "Q3". The number always
comes from the registry, never from the session's own count.

## Commands

`q` is on the PATH (set-up step 2). Run it directly, without a `PILOT_DIR=…` prefix: the variable, when
used, is already set for every session through `settings.json`.

```bash
q new --source <slug> [--reco "<recommendation>"] [--parent Q4] "<question>"   # prints Q<n> or Q4.<n>
q answer Q<n> "<answer>"                                                         # records the human's answer
q list [--open] [--day YYYY-MM-DD]                                               # today; --open alone: open ones of every day
```

Numbers restart at Q1 each day. `q list --open` shows open questions of every day, older ones prefixed by
their date. To answer an older one, pass its day: `q answer --day 2026-01-02 Q1 "<answer>"`; or renumber it
today with `q new` and mention the old number.

## Rules

- A sub-session registers, then sends the question to the pilot; it never asks the human itself.
- Only the pilot asks the human: in batches, each line starting `Q<n> —`,
  recommendation first.
- Always go through `q`, never write or edit the registry files by hand: `q` takes the lock and computes the
  number; a hand-written line can duplicate a number another session just took.
- The hook `q-registered` blocks any assistant turn that announces `Q<n> —` absent from today's registry.

## Storage

`$PILOT_DIR/questions/YYYY-MM-DD.jsonl` (default `PILOT_DIR=~/.local/state/claude-pilot`). One JSON event
per line (`new` or `answer`); a question's state is the merge of its events. Writers take a file lock, so two
sessions registering at once get distinct numbers. Put `PILOT_DIR` inside the pilot repo if you want the
registry versioned.
