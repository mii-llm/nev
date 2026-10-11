"""Label and accounting regressions for the external bilingual diagnostic."""
import json
from pathlib import Path
import tempfile
import unittest

from experiments.lumi.prepare_okapi_eval import mc_options, read_objects
from experiments.lumi.okapi_eval import metrics


class OkapiEvalTests(unittest.TestCase):
    def test_each_language_keeps_its_gold_after_option_permutation(self):
        en = {"option_a": "wrong", "option_b": "correct", "answer": "B"}
        it = {"option_a": "corretto", "option_b": "errato", "answer": "A"}
        self.assertEqual(mc_options(en), (["wrong", "correct"], 1))
        self.assertEqual(mc_options(it), (["corretto", "errato"], 0))

    def test_empty_option_does_not_shift_gold_letter(self):
        self.assertEqual(mc_options({"option_a": "x", "option_b": "", "option_c": "y", "answer": "C"}),
                         (["x", "y"], 1))

    def test_pretty_json_and_duplicate_source_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.jsonl"
            path.write_text(json.dumps({"id": "a", "text": "x\ny"}, indent=2) + "\n" + json.dumps({"id": "b"}))
            self.assertEqual(set(read_objects(path)), {"a", "b"})
            path.write_text('{"id":"a"}\n{"id":"a"}')
            with self.assertRaises(ValueError):
                read_objects(path)

    def test_unsupported_is_wrong_and_chance_uses_all_rows(self):
        value = metrics([{"status": "ok", "correct": True, "options": 4, "nll": .2},
                         {"status": "unsupported", "correct": False, "options": 2}])
        self.assertEqual(value["accuracy"], .5)
        self.assertEqual(value["answered"], 1)
        self.assertEqual(value["chance"], .375)
        self.assertAlmostEqual(value["chance_corrected"], .2)
        self.assertLess(value["accuracy_wilson_95"][0], .5)
        self.assertGreater(value["accuracy_wilson_95"][1], .5)


if __name__ == "__main__":
    unittest.main()
