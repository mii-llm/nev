import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/lumi"))
from practical_data import generate as v1, sha, validate_pairs
from practical_data_v2 import generate, BANKS, RULES, FAMILIES
from run_practical_v2 import calibrate, should_stop


class PracticalV2Tests(unittest.TestCase):
    def test_fresh_pairs_and_fact_configurations_exclude_every_v1_panel(self):
        previous = {sha([r["supervision"]["decision"]["task"], r["provenance"]["facts"]])
                    for rows in v1().values() for r in rows}
        current = generate()
        validate_pairs(current)
        seen = set(previous)
        for split, rows in current.items():
            for r in rows:
                if r["language"] != "en":
                    continue
                key = sha([r["supervision"]["decision"]["task"], r["provenance"]["facts"]])
                self.assertNotIn(key, seen)
                seen.add(key)
                self.assertIn(r["provenance"]["template_id"], BANKS[split])
        self.assertEqual(current, generate())

    def test_wording_banks_are_disjoint_in_both_languages(self):
        seen_ids = set()
        for bank in BANKS.values():
            self.assertFalse(seen_ids.intersection(bank))
            seen_ids.update(bank)
        for family in FAMILIES:
            self.assertEqual(len(RULES[family]), len(seen_ids))
            for lang_index in (0, 1):
                self.assertEqual(len({pair[lang_index] for pair in RULES[family]}), len(seen_ids))

    def test_rule_rendering_keeps_gold_out_of_model_request(self):
        for rows in generate().values():
            for r in rows:
                self.assertNotIn("supervision", r["request"])
                self.assertNotIn("facts", r["request"])
                self.assertNotIn("{", r["request"]["questions"]["decision"]["instructions"])
                q = r["request"]["questions"]["decision"]
                keys = list(q["criteria"]) if q["type"] != "score" else [str(i) for i in range(len(q["criteria"]))]
                self.assertIn(r["supervision"]["decision"]["gold"], keys)

    def test_threshold_selection_uses_policy_split_not_temperature_fit(self):
        base = [{"logits": [5., 0.], "label": 0, "language": lang, "source_family": "demo"}
                for lang in ("en", "it") for _ in range(100)]
        bad = [{**r, "label": 1} for r in base]
        cfg = {"calibration_temperature_grid": {"low": .5, "high": 2., "points": 3},
               "confidence_threshold_grid": [.5, .9], "calibration_min_accepted_per_language": 30,
               "calibration_risk_target": .1}
        result = calibrate(base, bad, cfg)
        self.assertIsNone(result["threshold"])
        self.assertEqual(result["temperature_fit"]["overall"]["accuracy"], 1.)
        self.assertEqual(result["calibration"]["overall"]["accuracy"], 0.)

    def test_early_stopping_waits_for_minimum_and_ignores_ineligible_gains(self):
        cfg = {"minimum_updates_before_early_stop": 512, "early_stop_patience": 3}
        bad = [{"eligible": False, "dev": {"macro_nll": x}} for x in (.4, .3, .2, .1)]
        self.assertFalse(should_stop(bad, .5, 384, cfg))
        self.assertTrue(should_stop(bad, .5, 512, cfg))
        good = [{"eligible": True, "dev": {"macro_nll": x}} for x in (.4, .3, .2, .1)]
        self.assertFalse(should_stop(good, .5, 512, cfg))
        plateau = [{"eligible": True, "dev": {"macro_nll": x}} for x in (.1, .2, .2, .2)]
        self.assertTrue(should_stop(plateau, .5, 512, cfg))


if __name__ == "__main__":
    unittest.main()
