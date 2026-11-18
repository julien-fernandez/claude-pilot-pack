---
name: voice-session
description: Prepare a short decision dossier the human takes into the Claude app's voice mode (in the car, on a walk), then bring the transcript back and apply what was decided. Use when the human says "prepare a voice session", "I'll be out, prepare my decisions", "decide out loud", or "bring the voice session back".
---

# Voice sessions

The human thinks better out loud and away from the screen. The pilot prepares; the human decides by voice;
the pilot applies.

## Prepare

1. Collect candidates: `q list --open`, sub-session reports waiting for a decision, PRs waiting for review.
2. **Check every item before it enters the dossier.** Search the registry (`q list` over the last days), the
   state files, the reports and the recent commits. Drop what is already done or already decided. This check
   is the step that makes sessions finish: without it, the human spends the session saying "already done".
3. Keep **15 items at most**, most important first. A dossier of 40 or 50 questions does not get finished.
4. Write the dossier from `templates/dossier.md`: per item, context in two sentences, options, recommendation,
   what happens without an answer. Written to be heard: short sentences, no tables, no links to open.
5. Open the conversation for the human:
   - in the Claude app or claude.ai, a new conversation (a Project keeps the instructions),
   - attach the dossier,
   - send the first message yourself or leave it ready: "Read me item 1, wait for my decision, note it,
     go on. At the end, read back every decision.",
   - give it a title the human recognises on the phone, e.g. `VOICE TO RUN — <date>`.
   Doing this through a browser automation tool is possible; the pack does not ship one.
6. Tell the human it is ready. They open it on the phone and switch to voice mode.

## Bring it back

1. Get the transcript: paste it, or export the conversation from claude.ai.
2. Save it next to the dossier (`voice/<date>/transcript.md`).
3. For each item: record the decision with `q answer Q<n> "<decision>"`, forward it to the sub-session
   concerned, and do at once what was decided and is safe to do. Publishing, sending or spending still
   waits for an explicit yes.
4. Items not reached stay open in the registry for the next session.
5. Write a short summary: decided, applied, left open.
