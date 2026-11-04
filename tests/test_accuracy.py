import json
import tempfile
import unittest
from pathlib import Path

from scripts.evaluate_accuracy import load_examples, summarize


class AccuracyTests(unittest.TestCase):
    def test_uncertain_and_errors_do_not_inflate_success(self):
        rows = [
            dict(expected=e, outcome=o)
            for e, o in [
                ("human", "correct"),
                ("human", "human_flagged_ai"),
                ("human", "uncertain"),
                ("ai", "correct"),
                ("ai", "ai_called_human"),
                ("ai", "not_checked"),
                ("ai", "error"),
            ]
        ]
        result = summarize(rows)
        self.assertEqual(result["correct_among_clear_answers_percent"], 50)
        self.assertEqual(result["clear_answer_percent"], 57.1)
        self.assertEqual(result["human_false_alarm_percent"], 33.3)
        self.assertEqual(result["ai_called_human_percent"], 25)
        self.assertEqual(result["not_checked"], 1)
        self.assertEqual(result["errors"], 1)

    def test_no_decisions_has_no_accuracy(self):
        self.assertIsNone(
            summarize([dict(expected="ai", outcome="uncertain")])[
                "correct_among_clear_answers_percent"
            ]
        )
        self.assertIsNone(summarize([])["human_false_alarm_percent"])

    def test_duplicate_text_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.jsonl"
            p.write_text(
                "\n".join(
                    json.dumps(dict(id=str(i), text=t, label="human"))
                    for i, t in enumerate(["same text", "same   text"])
                )
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_examples(p)

    def test_invalid_label_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.jsonl"
            p.write_text(
                json.dumps(dict(id="1", text="Some text", label="probably ai"))
            )
            with self.assertRaisesRegex(ValueError, "human/ai"):
                load_examples(p)


if __name__ == "__main__":
    unittest.main()
