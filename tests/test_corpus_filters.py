from experiments.lumi.corpus_filters import filter_records


def row(rid, group, text, gold):
    return {"record_id": rid, "group_id": group, "request": {"state": text},
            "supervision": {"q": {"gold": gold}}, "provenance": {"text_sha256": text}}


def test_conflicting_groups_and_siblings_removed_regardless_of_order():
    rows = [row("a", "g1", "same", "true"), row("b", "g2", "same", "false"),
            row("c", "g1", "sibling", "true"), row("d", "ok", "clean", "false")]
    for records in (rows, list(reversed(rows))):
        kept, audit = filter_records(records, set())
        assert kept == [rows[-1]]
        assert audit["conflicting_label_group_ids"] == ["g1", "g2"]
        assert audit["conflicting_request_count"] == 1


def test_protected_text_excludes_whole_group_and_consistent_duplicates_collapse():
    rows = [row("a", "g1", "heldout", "true"), row("b", "g1", "sibling", "true"),
            row("c", "g2", "clean", "false"), row("d", "g3", "clean", "false")]
    kept, audit = filter_records(rows, {("text", "heldout")})
    assert kept == [rows[2]]
    assert audit["removed_record_ids"] == ["a", "b"]
    assert audit["exact_duplicate_request_ids"] == ["d"]
    kept, _ = filter_records(rows, {("text", "heldout")}, deduplicate=False)
    assert kept == rows[2:]
