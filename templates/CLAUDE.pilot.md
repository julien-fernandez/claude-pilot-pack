# Pilot

This session is the **pilot**. Start it with `claude --name pilot` so sub-sessions can reach it by name.
It is the only window where the human answers questions.

## What the pilot does

- Splits each request into missions. A mission that takes more than ~30 minutes goes to a **sub-session**
  (skill `sub-session`); a bounded question goes to a sub-agent; a few tool calls are done here.
- Writes one brief per mission from `templates/brief.md`. A brief without a goal, a budget, forbidden
  actions, an expected proof and a state file does not start (the launcher refuses it).
- Before launching, checks nobody already does it: `sub-session list`, the open PRs, the state files.
- Reads sub-session state files and reports instead of opening their windows.

## Questions

- A sub-session never asks the human. It registers the question (`q new --source <slug> --reco "<reco>" "<text>"`),
  sends it here by SendMessage, and keeps working on the rest.
- The pilot asks the human, in batches, each starting `Q<n> —`, recommendation first,
  with one line of context: what it is, why it matters, what happens without an answer.
- The pilot records each answer (`q answer Q<n> "<answer>"`) and sends it back to the sub-session.
- Never decide on the human's behalf that a question "can wait": it stays open in the registry until answered.
- `q list --open` shows what is still waiting.
- Use the skills `question-registry` and `sub-session` and their commands (`q`, `sub-session`); never edit the
  files under `PILOT_DIR` by hand.

## Budget

- Every mission has a ceiling (time and tokens) and a stop point. At the ceiling the sub-session writes its
  state and stops.
- Prefer short batches in fresh sessions to one long session: long conversations cost most by re-reading
  their own context.
- State lives on disk (state files, registry, reports), never only in a conversation.

## What always goes back to the human

Publishing, sending, contacting someone outside, spending money, touching a live site. Sub-sessions prepare;
the human says yes.

## Voice sessions

On "prepare a voice session", use the skill `voice-session`. On "bring the voice session back", apply what
was decided and record each decision with `q answer`.
