import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/lumi"))
from compare_latest import common_panel, existing_practical, practical_rows, decode_answer


class ComparisonTests(unittest.TestCase):
    def test_laya_native_score_uses_argmax_and_noul_uses_true_probability(self):
        choice, _, _ = decode_answer({"type": "score", "criteria": ["low", "medium", "high"]},
                                     {"score": 1.1, "probabilities": {"0": .4, "1": .1, "2": .5}})
        self.assertEqual(choice, "2")
        choice, probs, tied = decode_answer({"type": "noul", "criteria": {"true": "Yes", "false": "No"}}, {"noul": .6})
        self.assertEqual(choice, "true")
        self.assertEqual(probs["false"], .4)
        self.assertFalse(tied)
    def setUp(self):
        self.rows = [{"id": f"{pair}/{lang}", "pair_id": str(pair), "language": lang,
                      "family": "demo", "expected": "a", "options": 2,
                      "status": "ok", "correct": True}
                     for pair in range(3) for lang in ("en", "it")]

    def test_common_support_excludes_both_languages_when_one_cannot_fit(self):
        other = copy.deepcopy(self.rows)
        other[1].update(status="unsupported", correct=False)
        report = common_panel({"a": self.rows, "b": list(reversed(other))})
        self.assertEqual(report["common_bilingual_requests"], 4)
        self.assertEqual(report["full"]["b"]["overall"]["accuracy"], 5/6)
        self.assertEqual(report["common_bilingual"]["b"]["overall"]["accuracy"], 1)
        self.assertEqual(report["common_bilingual"]["a"]["by_language"]["en"]["n"], 2)

    def test_changed_gold_or_duplicate_predictions_are_rejected(self):
        other = copy.deepcopy(self.rows)
        other[0]["expected"] = "b"
        with self.assertRaises(AssertionError):
            common_panel({"a": self.rows, "b": other})
        with self.assertRaises(AssertionError):
            common_panel({"a": self.rows, "b": self.rows[:-1]+[self.rows[0]]})

    def test_practical_gold_and_argmax_use_semantic_keys(self):
        records = [{"record_id": "x/en", "group_id": "x", "language": "en", "source_family": "refund",
                    "request": {"state": "Example", "questions": {"q": {"type": "noul", "criteria": {"false": "No", "true": "Yes"}}}},
                    "supervision": {"q": {"gold": "true"}}}]
        panel = practical_rows(records)
        rows = existing_practical([{"record_id": "x/en", "logits": [-1, 2], "keys": ["false", "true"], "label": 1}], panel)
        self.assertEqual(rows[0]["choice"], "true")
        self.assertTrue(rows[0]["correct"])
        self.assertEqual(rows[0]["options"], 2)


if __name__ == "__main__":
    unittest.main()
