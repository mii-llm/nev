"""Scaling finite policy generators must preserve split isolation and siblings."""
import copy

import pytest

from decision_model.data import (
    FAMILIES, _check_disjoint, _drop_policy_split_collisions, _policy_record,
    bucket, contrastive_generate,
)


def record(group, text, source="contrastive"):
    return {"group_id": group, "source_family": source,
            "provenance": {"text_sha256": text}}


def test_collision_drops_whole_groups_without_reassigning_holdouts():
    splits = {"train": [record("a", "shared"), record("a", "sibling"), record("safe", "unique")],
              "dev": [record("b", "shared"), record("b", "other")],
              "test": [record("held", "heldout")]}
    held = copy.deepcopy(splits["test"])
    with pytest.raises(ValueError):
        _check_disjoint(splits)
    audit = _drop_policy_split_collisions(splits)
    _check_disjoint(splits)
    assert audit["dropped_group_ids"] == ["a", "b"]
    assert audit["dropped_records_by_split"] == {"train": 2, "dev": 2, "test": 0}
    assert splits["train"] == [record("safe", "unique")]
    assert splits["dev"] == [] and splits["test"] == held


def test_public_collisions_still_fail_and_same_split_variants_survive():
    splits = {"train": [record("p", "same", "public"), record("a", "repeat"), record("b", "repeat")],
              "dev": [record("q", "same", "public")]}
    original = copy.deepcopy(splits)
    assert _drop_policy_split_collisions(splits)["conflicting_texts"] == 0
    assert splits == original
    with pytest.raises(ValueError):
        _check_disjoint(splits)


def test_actual_tenfold_generator_remains_disjoint_after_filtering():
    raw, _ = contrastive_generate(720, "20260924-pool", [f for f in FAMILIES if f != "deadline"])
    splits = {s: [] for s in ("train", "dev", "calibration", "test")}
    for item in raw:
        r = _policy_record(item, "pool")
        split = bucket(r["group_id"], 20260924)
        r["split"] = split
        splits[split].append(r)
    original = copy.deepcopy(splits)
    audit = _drop_policy_split_collisions(splits)
    assert audit["conflicting_texts"] > 0
    _check_disjoint(splits)
    dropped = set(audit["dropped_group_ids"])
    for split, records in splits.items():
        assert records == [r for r in original[split] if r["group_id"] not in dropped]
        assert records
