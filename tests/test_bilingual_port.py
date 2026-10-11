"""Regression checks for independent teachers, bilingual splits and backend selection."""
import copy
import json
import random
from collections import Counter

import pytest
import torch

from decision_model.data import custom_records
from decision_model.render import LLAMA_SPECIAL, SPECIAL, delimiter_ids
from decision_model.targets import collection_hash, collection_path, teacher_identity
from decision_model.train import epoch_order


def test_balanced_updates_preserve_every_record_and_partial_update():
    records = [{"record_id": f"{lang}{i}", "language": lang} for lang in ("it", "en") for i in range(7)]
    order = epoch_order(records, random.Random(1), language_balance={"it": .5, "en": .5}, accumulation=8)
    assert sorted(r["record_id"] for r in order) == sorted(r["record_id"] for r in records)
    for start in range(0, len(order), 8):
        counts = Counter(r["language"] for r in order[start:start + 8])
        assert counts["it"] == counts["en"]
    assert order == epoch_order(records, random.Random(1), language_balance={"it": .5, "en": .5}, accumulation=8)
    with pytest.raises(ValueError, match="equal nonzero"):
        epoch_order(records[:-1], random.Random(1), language_balance={"it": .5, "en": .5})
    with pytest.raises(ValueError, match="even accumulation"):
        epoch_order(records, random.Random(1), language_balance={"it": .5, "en": .5}, accumulation=3)
    with pytest.raises(ValueError, match="needs language"):
        epoch_order([{"record_id": "missing"}], random.Random(1), language_balance={"it": .5, "en": .5})


def test_translation_group_and_language_survive_custom_data_loading(tmp_path):
    path = tmp_path / "paired.jsonl"
    rows = [{"state": state, "language": lang, "group_id": "same-underlying-case",
             "questions": {"q": {"type": "noul", "instructions": "Duplicate?", "label": "true"}}}
            for lang, state in (("it", "Mi avete addebitato due volte la stessa fattura."),
                                ("en", "You charged me twice for the same invoice."))]
    path.write_text("\n".join(json.dumps(r) for r in rows))
    recs, _ = custom_records({"path": str(path), "source_family": "paired"}, 0, set())
    assert {r["language"] for r in recs} == {"it", "en"}
    assert recs[0]["group_id"] == recs[1]["group_id"]
    assert recs[0]["split"] == recs[1]["split"]
    assert recs[0]["record_id"] != recs[1]["record_id"]


def test_teacher_cache_tracks_teacher_and_dataset_not_student_identity(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"files": {"train.jsonl": {"sha256": "dataset-a"}}}))
    cfg = {"parent": "student", "revision": "student-revision", "data": {"out": str(tmp_path)},
           "teacher": {"out": str(tmp_path / "targets"), "dtype": "bfloat16", "batch_tokens": 1024,
                       "model": "teacher-a", "revision": "teacher-revision"}}
    assert teacher_identity(cfg) == ("teacher-a", "teacher-revision")
    first = collection_path(cfg)
    other = copy.deepcopy(cfg)
    other["teacher"]["model"] = "teacher-b"
    assert collection_path(other) != first
    other = copy.deepcopy(cfg)
    other["parent"] = "another-student"
    assert collection_hash(other, tmp_path) == collection_hash(cfg, tmp_path)
    manifest.write_text(json.dumps({"files": {"train.jsonl": {"sha256": "dataset-b"}}}))
    assert collection_path(cfg) != first
    del cfg["teacher"]["revision"]
    with pytest.raises(ValueError, match="independent teacher"):
        teacher_identity(cfg)
    del cfg["teacher"]["model"]
    assert teacher_identity(cfg) == ("student", "student-revision")
    assert collection_path(cfg) == tmp_path / "targets" / "student-revi" / "targets.jsonl"


class TokenizerStub:
    unk_token_id = None

    def __init__(self, profile):
        self.ids = dict(zip(profile, range(10, 15)))

    def convert_tokens_to_ids(self, token):
        return self.ids.get(token)

    def encode(self, token, **kwargs):
        return [self.ids[token]]


@pytest.mark.parametrize("profile", [SPECIAL, LLAMA_SPECIAL])
def test_delimiters_accept_both_profiles_and_reject_collisions(profile):
    tok = TokenizerStub(profile)
    assert list(delimiter_ids(tok).values()) == list(range(10, 15))
    tok.ids[profile[-1]] = tok.ids[profile[0]]
    with pytest.raises(ValueError, match="distinct atomic"):
        delimiter_ids(tok)


@pytest.mark.parametrize("family", ["llama", "qwen3"])
def test_decoder_loads_both_supported_families_without_random_missing_weights(tmp_path, family):
    from transformers import LlamaConfig, LlamaModel, Qwen3Config, Qwen3Model
    from decision_model.backbones.decoder import load_backbone
    config_cls, model_cls = (LlamaConfig, LlamaModel) if family == "llama" else (Qwen3Config, Qwen3Model)
    config = config_cls(vocab_size=32, hidden_size=16, intermediate_size=32, num_hidden_layers=1,
                        num_attention_heads=4, num_key_value_heads=2, head_dim=4)
    original = model_cls(config).eval()
    original.save_pretrained(tmp_path)
    loaded = load_backbone(tmp_path, device="cpu", local_files_only=True)
    assert loaded.config.model_type == family
    for key, value in original.state_dict().items():
        torch.testing.assert_close(loaded.state_dict()[key], value)
