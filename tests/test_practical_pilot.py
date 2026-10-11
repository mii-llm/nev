"""Cheap independent checks for the pilot's boundaries, splits and confidence policy."""
import copy
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/lumi"))
from practical_data import generate, oracle, validate_pairs, sha
from run_practical import calibrate, guard_pass, metrics, probabilities, wilson_upper


class PracticalPilotTests(unittest.TestCase):
    def test_gold_boundaries_and_missing_data_precedence(self):
        self.assertEqual(oracle("refund", {"limit": 30, "days": 30, "proof": True}), "approve")
        self.assertEqual(oracle("refund", {"limit": 30, "days": 31, "proof": True}), "deny")
        self.assertEqual(oracle("refund", {"limit": 30, "days": 31, "proof": None}), "clarify")
        for hours, expected in ((24, "2"), (25, "1"), (72, "1"), (73, "0")):
            self.assertEqual(oracle("urgency", {"urgent": 24, "soon": 72, "hours": hours}), expected)
        f = {"verified": True, "limit": 50, "amount": 50, "retry_limit": 3, "attempts": 2}
        self.assertEqual(oracle("escalation", f), "false")
        self.assertEqual(oracle("escalation", {**f, "attempts": 3}), "true")
        self.assertEqual(oracle("escalation", {**f, "verified": False}), "true")
        f = {"priority": ["billing", "delivery", "access"], "billing": True, "delivery": True,
             "access": False, "amount": 19, "minimum": 20}
        self.assertEqual(oracle("routing", f), "delivery")
        self.assertEqual(oracle("routing", {**f, "amount": 20}), "billing")

    def test_deterministic_balanced_disjoint_semantic_facts(self):
        data = generate()
        self.assertEqual(data, generate())
        validate_pairs(data)
        seen = set()
        for split, rows in data.items():
            pairs = [r for r in rows if r["language"] == "en"]
            signatures = {sha([r["source_family"], r["provenance"]["facts"]]) for r in pairs}
            self.assertEqual(len(signatures), len(pairs))
            self.assertFalse(seen & signatures)
            seen |= signatures
            for family in {r["source_family"] for r in pairs}:
                counts = Counter(r["supervision"]["decision"]["gold"] for r in pairs if r["source_family"] == family)
                self.assertLessEqual(max(counts.values())-min(counts.values()), 1)
        with self.assertRaises(ValueError):
            validate_pairs({"train": data["train"], "test": data["train"][:2]})

    def test_incomplete_or_misaligned_pairs_fail(self):
        data = {"train": generate()["train"][:2]}
        bad = copy.deepcopy(data)
        bad["train"][1]["supervision"]["decision"]["gold"] = "invalid"
        with self.assertRaises(ValueError):
            validate_pairs(bad)
        with self.assertRaises(ValueError):
            validate_pairs({"train": data["train"][:1]})

    def test_temperature_and_abstention_are_not_accuracy(self):
        rows = [{"logits": [4., 0.], "label": 1}]
        self.assertEqual(metrics(rows, 1.)["accuracy"], metrics(rows, 4.)["accuracy"])
        self.assertEqual(metrics(rows, 1., None)["coverage"], 0)
        self.assertIsNone(metrics(rows, 1., None)["accepted_error_rate"])
        self.assertEqual(metrics(rows, 1., .9)["accepted_error_rate"], 1.)
        self.assertLess(max(probabilities([4., 0.], 4)), max(probabilities([4., 0.], 1)))
        self.assertAlmostEqual(wilson_upper(0, 100), .03699, places=4)

    def test_calibration_does_not_accept_a_bad_language(self):
        rows = [{"logits": [5., 0.], "label": 0 if lang == "en" else 1,
                 "source_family": "demo", "language": lang} for lang in ("en", "it") for _ in range(100)]
        cfg = {"calibration_temperature_grid": {"low": 1., "high": 2., "points": 3},
               "confidence_threshold_grid": [.5, .9], "calibration_min_accepted_per_language": 30,
               "calibration_risk_target": .1}
        self.assertIsNone(calibrate(rows, cfg)["threshold"])

    def test_guard_checks_both_languages(self):
        base = {"macro_nll": .5, "by_language": {"en": {"accuracy": .8}, "it": {"accuracy": .8}}}
        candidate = copy.deepcopy(base)
        candidate["by_language"]["it"]["accuracy"] = .7
        self.assertFalse(guard_pass(candidate, base, {"max_guard_nll_increase": .05, "max_guard_accuracy_drop": .02}))


if __name__ == "__main__":
    unittest.main()
