"""Protect labels, rule semantics and teacher-comparison accounting."""
import copy
import math
import json

import pytest

from decision_model.data import TRAIN_SHAPES, _policy_record, composition_generate
from experiments.lumi.bilingual_data import (composition_it, normalize_request,
    translate_request, translation_error, validate_pair)
from experiments.lumi.run_bilingual_pilot import summarize


def test_translation_keeps_ids_types_order_and_numbers():
    req = {"state": "Paid 25 on 2026-09-28.", "questions": {
        "intent": {"type": "choice", "instructions": "Pick intent", "criteria": {"return_item": None, "help": "Help"}},
        "urgent": {"type": "noul", "instructions": "Urgent?"},
        "level": {"type": "score", "instructions": "Rate", "criteria": ["Low", "High"]}}}
    normalized = normalize_request(req)
    translated = translate_request(normalized, lambda s: "IT " + s)
    validate_pair(normalized, translated)
    assert req["questions"]["intent"]["criteria"]["return_item"] is None
    assert normalized["questions"]["intent"]["criteria"]["return_item"] == "return item"
    assert translation_error(req["state"], "Pagato 25 il 2026-09-28.") is None
    assert translation_error(req["state"], "Pagato 250 il 2026-09-28.") == "numbers_or_dates_changed"
    assert translation_error("What is the capital of Italy?", "La capitale è Roma.") == "question_structure_changed"
    bad = copy.deepcopy(translated)
    bad["questions"]["intent"]["criteria"] = {"other": "Altro", "help": "Aiuto"}
    with pytest.raises(AssertionError):
        validate_pair(normalized, bad)


def test_all_composition_shapes_render_from_gold_certificates():
    for raw in composition_generate(2, "test-bilingual", TRAIN_SHAPES):
        r = _policy_record(raw, "train")
        translated = composition_it(r)
        validate_pair(r["request"], translated)
        label = r["supervision"]["decision"]["gold"]
        assert (label == "accept") == r["provenance"]["certificate"]["label"]
        assert translated["state"]["policy"].startswith("Approva se e solo se")


def test_comparison_balances_source_language_cells_and_records():
    def row(rid, lang, source, p):
        return {"record_id": rid, "language": lang, "source_family": source,
                "type": "noul", "probs": [p, 1 - p], "label": 0}
    # Repeating questions inside a record must not increase its selection weight.
    rows = [row("a", "it", "many", .9)] * 5 + [row("b", "en", "few", .2)]
    got = summarize(rows)
    assert got["source_language_macro_record_nll"] == pytest.approx((-math.log(.9) - math.log(.2)) / 2)
    assert got["overall"]["accuracy"] == pytest.approx(5 / 6)


def test_external_translation_cache_finalizes_without_loading_teacher(tmp_path, monkeypatch):
    import transformers
    from decision_model.data import SPLITS, digest, load_split, text_hash, write_json, write_jsonl
    from experiments.lumi import bilingual_data as builder
    from experiments.lumi.run_bilingual_pilot import approved_data
    english = tmp_path / "english"
    english.mkdir()
    manifest = {"files": {}, "sources": {}, "roles": {}}
    identity = {"model": "large-teacher", "revision": "pinned", "backend": "vllm"}
    cache = [{"source": "Ready?", "it": "Pronto?", "error": None, "translator": identity}]
    for split in SPLITS:
        state = f"state_{split}"
        record = {"record_id": split, "group_id": split, "split": split, "source_family": "fixture",
                  "schema_family": "fixture", "request": {"state": state, "questions": {
                      "q": {"type": "noul", "instructions": "Ready?"}}},
                  "supervision": {"q": {"gold": "true"}}, "provenance": {"text_sha256": text_hash(state)}}
        path = english / f"{split}.jsonl"
        write_jsonl(path, [record])
        manifest["files"][path.name] = {"records": 1, "sha256": digest(path)}
        cache.append({"source": state, "it": f'stato_\\"{split}\\"', "error": None, "translator": identity})
    write_json(english / "manifest.json", manifest)
    write_json(tmp_path / "base-recipe.json", {"parent": "student", "revision": "r", "data": {"context": {}}})
    cache_file = tmp_path / "cache.jsonl"
    write_jsonl(cache_file, cache)
    loaded = []
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", lambda name, **kw: loaded.append(name) or object())
    monkeypatch.setattr(builder, "context_size", lambda *a: 1)
    reviewed = tmp_path / "reviewed.json"
    write_json(reviewed, {"Ready?": "È pronto?"})
    builder.run(tmp_path, 1, cache_file=cache_file, translator=identity, finalize_only=True, prompt_version="external", reviewed_path=reviewed)
    assert loaded == ["student"]
    assert [r["language"] for r in load_split(tmp_path / "data", "train")] == ["en", "it"]
    it = load_split(tmp_path / "data", "train")[1]
    assert it["request"]["state"] == 'stato_"train"'
    assert it["request"]["questions"]["q"]["instructions"] == "È pronto?"
    review = tmp_path / "data" / "quality-review.json"
    write_json(review, {"status": "rejected", "manifest_sha256": digest(tmp_path / "data" / "manifest.json")})
    with pytest.raises(AssertionError, match="not approved"):
        approved_data(tmp_path)
    write_json(review, {"status": "approved_for_pilot", "manifest_sha256": digest(tmp_path / "data" / "manifest.json")})
    approved_data(tmp_path)
    write_json(review, {"status": "approved_for_pilot", "manifest_sha256": "stale"})
    with pytest.raises(AssertionError, match="changed"):
        approved_data(tmp_path)
