---
name: use-cases
description: Write a catalogue of concrete, replayable use cases for a tool, a pack of skills or an app (role → moment → scenario), each one played in an isolated bench or listed as not testable with its reason. Use before saying a pack or a feature "works", when a sub-session must prove a delivery, "write the use cases", "how many cases do we cover", "200 use cases", "is every skill tested", or when a report claims "done" without a list of what was tried.
---

# Use cases

A use case exists only to produce a test. A case without concrete values and an expected result is
decoration: drop it. The catalogue is a file of data (one JSON object per line), not prose, so a runner can play
it and a report can be built from it.

## Vocabulary

| Term | What it is | Example |
|---|---|---|
| `role` | the hat someone wears at that instant, not the person | "sub-session working from a brief" |
| `moment` | a situation with its physical constraints | "the human is leaving: phone only, no screen" |
| `job` | the sentence of a moment: *When… I want… so I can…* | "When I need a decision, I want it numbered, so I can keep working." |
| `scenario` | one instance with real values, replayable | `q new --source s1 "Ship on Friday?"` prints `Q1` |
| anti-usage | a request that only shares a word with the tool and must NOT trigger it | "write a quiz of three questions" |

One person carries several roles in a day; model the roles, never the person. A moment carries its
constraints as mandatory fields (no screen, no network, two sessions at the same second, midnight passes).

## Steps

1. **Roles** (5-8): list who acts on the tool, including the agents (pilot session, background session) and the
   evaluator who tries it without installing.
2. **Moments** (10-15): for each role, the situations where the tool is used, with their constraints. Always add
   three moments: *first install*, *malformed input*, *anti-usage*.
3. **Jobs**: one *When… I want… so I can…* per case. If you cannot write the "so I can", the case has no reason.
4. **Scenarios**: concrete values and one check each. Three kinds:
   - `script` — a shell command and its expected exit code and output regex. Cheap, deterministic.
   - `agent` — a prompt played with `claude -p` and the skill expected to load (or `none` for anti-usage),
     plus an optional shell check of the result (a file written, an answer recorded).
   - `not testable` — the reason it cannot run in the bench (needs a phone, a human voice, another machine,
     hours of run, spending money). Listing it is mandatory: it is what the report's "Not verified" is made of.
5. **Spread** before writing many: every skill gets trigger phrases in each language its users speak, every
   script gets its refusals, every hook gets its pass and block, and anti-usage is about 10 %.
6. **Batches**: write all cases first, then play a first batch (the ones that touch each skill, each hook and
   each real background launch), report, and play the rest on the owner's word.
7. **Two-stage audit**: the bench is the mechanical stage (pass/fail with a trace). The judgement stage (is the
   brief good, is the report true) stays human; list those cases as `not testable` with that reason.

## Case format (`cases.jsonl`)

```json
{"id": "CU-001", "role": "INS", "moment": "M01", "job": "When…, I want…, so I can…", "kind": "script",
 "lot": 1, "cmd": "q new --source s1 \"Ship on Friday?\"", "expect_rc": 0, "expect_re": "^Q1$"}
{"id": "CU-029", "role": "SUB", "moment": "M02", "job": "…", "kind": "claude", "lot": 1,
 "prompt": "You need the human to decide …", "skill": "question-registry", "check": "q list --open | grep -q ."}
{"id": "CU-174", "role": "HUM", "moment": "M08", "job": "…", "kind": "nt", "lot": 2,
 "reason": "needs the phone app and a human voice"}
```

Generate the file from a short script (lists of phrases × moments) rather than by hand: the counts stay right and
a case is fixed in one place. Play it with the `isolated-bench` skill.

## Report

One table per batch: id, role, moment, verdict (OK / FAILED / NOT TESTABLE), trace (output tail, skills loaded,
hook blocks, turns). A failed case is a finding, not something to hide: write what it shows about the tool, or
about the bench if the bench was wrong (and fix the bench, then replay).
