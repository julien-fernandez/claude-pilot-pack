from helpers import PilotCase


class QuestionRegistry(PilotCase):
    def test_new_questions_are_numbered_from_q1(self):
        first = self.q("new", "--source", "alpha", "Which licence?")
        second = self.q("new", "--source", "beta", "Which language?")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout.strip(), "Q1")
        self.assertEqual(second.stdout.strip(), "Q2")

    def test_sub_questions_are_numbered_under_their_parent(self):
        self.q("new", "--source", "alpha", "Parent question")
        self.q("new", "--source", "alpha", "Other question")
        first = self.q("new", "--source", "alpha", "--parent", "q1", "Detail one")
        second = self.q("new", "--source", "alpha", "--parent", "Q1", "Detail two")
        after = self.q("new", "--source", "alpha", "Next top-level")
        self.assertEqual(first.stdout.strip(), "Q1.1")
        self.assertEqual(second.stdout.strip(), "Q1.2")
        self.assertEqual(after.stdout.strip(), "Q3")

    def test_unknown_parent_is_refused(self):
        result = self.q("new", "--source", "alpha", "--parent", "Q9", "Orphan")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Q9", result.stderr)

    def test_answered_questions_leave_the_open_list(self):
        self.q("new", "--source", "alpha", "--reco", "MIT", "Which licence?")
        self.q("new", "--source", "beta", "Which language?")
        answered = self.q("answer", "Q1", "MIT")
        self.assertEqual(answered.returncode, 0, answered.stderr)
        open_list = self.q("list", "--open").stdout
        full_list = self.q("list").stdout
        self.assertNotIn("Which licence?", open_list)
        self.assertIn("Q2", open_list)
        self.assertIn("Which language?", open_list)
        self.assertIn("Which licence?", full_list)
        self.assertIn("MIT", full_list)

    def test_answering_an_unknown_question_is_refused(self):
        result = self.q("answer", "Q4", "yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Q4", result.stderr)

    def test_list_reads_another_day(self):
        self.q("new", "--source", "alpha", "--day", "2026-01-02", "Old question")
        self.assertNotIn("Old question", self.q("list").stdout)
        self.assertIn("Old question", self.q("list", "--day", "2026-01-02").stdout)

    def test_concurrent_sessions_get_distinct_numbers(self):
        import subprocess
        from helpers import Q
        procs = [subprocess.Popen(["python3", str(Q), "new", "--source", f"s{i}", f"Question {i}"],
                                  stdout=subprocess.PIPE, text=True, env=self.env) for i in range(12)]
        numbers = sorted(p.communicate()[0].strip() for p in procs)
        self.assertEqual(numbers, sorted(f"Q{i}" for i in range(1, 13)))

    def test_open_list_includes_questions_left_open_on_earlier_days(self):
        self.q("new", "--source", "alpha", "--day", "2026-01-02", "Old open question")
        self.q("new", "--source", "alpha", "--day", "2026-01-03", "Old answered question")
        self.q("answer", "--day", "2026-01-03", "Q1", "done")
        open_list = self.q("list", "--open").stdout
        self.assertIn("2026-01-02 Q1", open_list)
        self.assertIn("Old open question", open_list)
        self.assertNotIn("Old answered question", open_list)
