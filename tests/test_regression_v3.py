"""Correctness transitions must remain paired with the exact input/gold identity."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/lumi"))
from regression_v3 import paired_delta


class RegressionPairingTest(unittest.TestCase):
    def setUp(self):
        self.before = [dict(id=str(i), expected="a", family="task", language="en",
                            pair_id=str(i), correct=value)
                       for i, value in enumerate((True, False, False))]

    def test_reordered_transitions(self):
        after = [{**r, "correct": not r["correct"]} for r in reversed(self.before)]
        result = paired_delta(self.before, after)["task/en"]
        self.assertEqual((result["n"], result["gained"], result["lost"]), (3, 2, 1))
        self.assertAlmostEqual(result["delta_percentage_points"], 100/3)

    def test_reject_changed_gold_and_duplicates(self):
        for after in ([{**r, "expected":"b"} for r in self.before],
                      [self.before[0], self.before[0], self.before[2]]):
            with self.assertRaises(AssertionError):
                paired_delta(self.before, after)
