import json

from helpers import PilotCase, HOOK


def entry(kind, content):
    return {"type": kind, "message": {"role": kind, "content": content}}


class QRegisteredHook(PilotCase):
    def transcript(self, *assistant_texts, earlier="", peer=False):
        lines = []
        if earlier:
            lines.append(entry("user", "old prompt"))
            lines.append(entry("assistant", [{"type": "text", "text": earlier}]))
        current = entry("user", "Another Claude session sent a message: answer is MIT")
        if peer:
            current["isMeta"] = True
        lines.append(current)
        for text in assistant_texts:
            lines.append(entry("assistant", [{"type": "text", "text": text}]))
            lines.append(entry("user", [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]))
        path = self.tmp / "transcript.jsonl"
        path.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
        return str(path)

    def hook(self, transcript, active=False):
        payload = json.dumps({"session_id": "s", "transcript_path": transcript,
                              "hook_event_name": "Stop", "stop_hook_active": active})
        return self.run_cmd(HOOK, stdin=payload)

    def test_blocks_a_turn_announcing_an_unregistered_question(self):
        result = self.hook(self.transcript("Here it is.\n\n**Q3 —** Which licence? Recommended: MIT"))
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(result.stdout)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("Q3", decision["reason"])
        self.assertIn("q new", decision["reason"])

    def test_lets_registered_questions_through(self):
        self.q("new", "--source", "t", "First")
        self.q("new", "--source", "t", "--parent", "Q1", "Detail")
        result = self.hook(self.transcript("Q1 — First\n- Q1.1 — Detail"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_ignores_turns_without_announced_questions_and_earlier_turns(self):
        result = self.hook(self.transcript("I answered Q7 as agreed.", earlier="Q9 — old unregistered"))
        self.assertEqual(result.stdout.strip(), "")

    def test_does_not_block_twice_in_a_row(self):
        result = self.hook(self.transcript("Q5 — invented"), active=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_a_message_from_another_session_starts_a_new_turn(self):
        result = self.hook(self.transcript("Recorded.", earlier="Q9 — old unregistered", peer=True))
        self.assertEqual(result.stdout.strip(), "")

    def test_ranges_and_code_blocks_are_not_announcements(self):
        text = "Q1 - Q4 are answered.\n```\nQ7 — example in a code block\n```"
        self.assertEqual(self.hook(self.transcript(text)).stdout.strip(), "")

    def test_a_corrupt_registry_line_does_not_disable_the_check(self):
        self.q("new", "--source", "t", "First")
        registry = next((self.pilot_dir / "questions").glob("*.jsonl"))
        with open(registry, "a") as f:
            f.write('{"q": "Q2"\n')
        result = self.hook(self.transcript("Q1 — First\nQ5 — invented"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Q5", result.stdout)
        self.assertNotIn("Q1,", result.stdout)
