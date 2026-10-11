"""Semantic protections for the bilingual benchmark preparation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from experiments.lumi.prepare_decision_subset import digest, map_request, mask, relative, request_texts, select, technical_literal
from experiments.lumi.translate_decision_subset import decode_translation, error, mask_numbers
from experiments.lumi.eval_decision_subset import check_ready


class DecisionSubsetTests(unittest.TestCase):
    def test_common_schema_words_are_translatable_and_url_punctuation_stays_outside_mask(self):
        for word in ("to", "from", "time", "date", "class", "regular", "album"):
            self.assertFalse(technical_literal(word))
        for word in ("PrimaryDB", "get_weather", "secure*pass123", "192.168.0.10"):
            self.assertTrue(technical_literal(word))
        masked, mapping = mask("host 'http://plgah.ca', database", set())
        self.assertEqual(mapping, {"__KEV_KEEP_A__": "http://plgah.ca"})
        self.assertEqual(masked, "host '__KEV_KEEP_A__', database")

    def test_translation_output_decodes_only_valid_json_strings(self):
        text = 'Una riga\nun "titolo".'
        self.assertEqual(decode_translation(json.dumps(text)), text)
        self.assertEqual(decode_translation(json.dumps(json.dumps(text))), text)
        self.assertEqual(decode_translation('plain \\n text'), 'plain \\n text')
        self.assertEqual(decode_translation('{"key": 12}'), '{"key": 12}')

    def test_numbers_are_protected_before_translation(self):
        source = 'At 9 PM, rating 4.5 on 2026-10-06, __KEV_KEEP_A__.'
        masked, mapping = mask_numbers(source)
        self.assertNotIn('9', masked)
        self.assertIn('__KEV_KEEP_A__', masked)
        restored = masked
        for key, value in mapping.items():
            restored = restored.replace(key, value)
        self.assertEqual(restored, source)

    def test_source_hash_paths_tolerate_scratch_symlink_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "real").mkdir()
            (root / "alias").symlink_to(root / "real", target_is_directory=True)
            (root / "real" / "source.json").write_text('{}')
            self.assertEqual(relative(root / "real" / "source.json", root / "alias"), "source.json")

    def test_overlap_audit_supports_structured_instructions(self):
        req = {"state": {"text": "premise", "count": 2},
               "questions": {"q": {"instructions": {"hypothesis": "hypothesis", "conditions": ["a", "b"]}}}}
        self.assertEqual(list(request_texts(req)), ["premise", "hypothesis", "a", "b"])

    def test_translation_cannot_change_ids_labels_or_tool_schema(self):
        row = {"family": "When2Call MCQ", "expected": {"q": "A"},
               "state": {"question": "Use get_weather for Rome?", "tools": [{"name": "get_weather",
                  "description": "Read weather", "parameters": {"type": "object", "required": ["city"],
                  "properties": {"city": {"type": "string", "description": "City name", "enum": ["Rome"]}}}}]},
               "questions": {"q": {"type": "choice", "instructions": "Choose response",
                             "criteria": {"A": "Call get_weather", "B": "Answer directly"}}}}
        before = copy.deepcopy(row)
        seen = []
        result = map_request(row, lambda s: seen.append(s) or "Italian: " + s)
        self.assertEqual(row, before)
        self.assertEqual(result["expected"], before["expected"])
        self.assertEqual(list(result["questions"]["q"]["criteria"]), ["A", "B"])
        tool = result["state"]["tools"][0]
        self.assertEqual(tool["name"], "get_weather")
        self.assertEqual(tool["parameters"]["required"], ["city"])
        self.assertEqual(tool["parameters"]["properties"]["city"]["enum"], ["Rome"])
        self.assertEqual(tool["parameters"]["properties"]["city"]["type"], "string")
        self.assertNotIn('"expected"', " ".join(seen))
        self.assertIn("get_weather", result["state"]["question"])
        with self.assertRaises(ValueError):
            map_request(row, lambda s: s.replace("__KEV_KEEP_A__", "weather"))

    def test_json_tool_calls_and_argument_literals_are_not_translated(self):
        call = '{"name": "add_server", "arguments": {"nickname": "PrimaryDB", "password": "secure*pass123"}}'
        row = {"family": "When2Call MCQ", "state": {"tools": [], "question": "Use PrimaryDB and secure*pass123?"},
               "questions": {"q": {"instructions": "Choose", "criteria": {"A": "Cannot do that", "B": call}}},
               "expected": {"q": "B"}}
        seen = []
        translated = map_request(row, lambda text: seen.append(text) or "Italian: " + text)
        self.assertEqual(translated["questions"]["q"]["criteria"]["B"], call)
        self.assertNotIn(call, seen)
        self.assertTrue(all("secure*pass123" not in s and "PrimaryDB" not in s for s in seen))
        self.assertIn("secure*pass123", translated["state"]["question"])

    def test_mask_and_numeric_checks(self):
        text, mapping = mask("Call get_weather(city='Rome') twice: 2 times.", {"get_weather", "city"})
        self.assertEqual(len(mapping), 2)
        self.assertIsNone(error(text, text.replace("Call", "Chiama").replace("twice", "due volte")))
        self.assertEqual(error(text, text.replace("2", "3")), "numbers_changed")
        self.assertEqual(error(text, text.replace("__KEV_KEEP_A__", "x")), "identifiers_changed")

    def test_selection_is_deterministic_and_group_disjoint(self):
        rows = [{"id": str(i), "family": "CLINC150+OOS", "split": "test", "expected": {"q1": "A"},
                 "questions": {"q1": {"instructions": "Classify:\n" + text}}}
                for i, text in enumerate(["same question", "same question", "different one", "a third one"])]
        a = select(rows)
        b = select(list(reversed(rows)))
        self.assertEqual(a, b)
        self.assertEqual(len({r["group_id"] for r in a}), 2)
        self.assertEqual({r["panel"] for r in a}, {"selection", "confirmation"})

    def test_when2call_samples_observed_gold_classes_not_number_of_choices(self):
        rows = [{"id": f"{label}:{i}", "family": "When2Call MCQ", "state": {"question": f"{label} query {i}"},
                 "expected": {"q": label}, "questions": {"q": {"criteria": {"A": "direct", "B": "tool", "C": "ask", "D": "cannot"}}}}
                for label in ("B", "C", "D") for i in range(110)]
        selected = select(rows)
        self.assertEqual(len(selected), 300)
        self.assertEqual(sum(r["panel"] == "selection" for r in selected), 150)
        self.assertEqual({r["expected"]["q"] for r in selected}, {"B", "C", "D"})

    def test_eval_refuses_unreviewed_or_changed_panels_and_unselected_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            for panel in ("selection", "confirmation"):
                (out / (panel + ".jsonl")).write_text('{}\n')
            hashes = {panel: digest(out / (panel + ".jsonl")) for panel in ("selection", "confirmation")}
            (out / "capacity-audit.json").write_text('[]\n')
            manifest = {"panel_sha256": hashes, "code_sha256": {}, "checkpoint_files_sha256": {"74000": {}},
                        "evaluation_files_sha256": {}, "capacity_audit_sha256": digest(out / "capacity-audit.json")}
            (out / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaises(FileNotFoundError):
                check_ready(out, "selection", "parent")
            review = {"status": "approved_for_diagnostic", "panel_sha256": hashes}
            (out / "quality-review.json").write_text(json.dumps(review))
            self.assertEqual(check_ready(out, "selection", "parent"), manifest)
            with self.assertRaises(FileNotFoundError):
                check_ready(out, "confirmation", "parent")
            (out / "selection-decision.json").write_text(json.dumps({"selection_sha256": hashes["selection"], "checkpoint_step": 74000}))
            check_ready(out, "confirmation", "74000")
            with self.assertRaises(AssertionError):
                check_ready(out, "confirmation", "142000")
            (out / "selection.jsonl").write_text('{"changed": true}\n')
            with self.assertRaises(AssertionError):
                check_ready(out, "selection", "parent")


if __name__ == "__main__":
    unittest.main()
