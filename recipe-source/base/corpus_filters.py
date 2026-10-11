"""Conservative filtering for full-source corpora, with auditable exclusions."""
import hashlib
import json


def identifiers(record):
    p = record["provenance"]
    result = {("group", record["group_id"])}
    if p.get("text_sha256"):
        result.add(("text", p["text_sha256"]))
    if p.get("repo") and p.get("row") is not None:
        result.add(("source_row", p["repo"], str(p.get("config")), str(p.get("split")), str(p["row"])))
    return result


def filter_records(records, forbidden, *, deduplicate=True):
    # Exclude siblings too: translations or contrastive states share a group.
    protected_groups = {r["group_id"] for r in records if identifiers(r) & forbidden}
    kept = [r for r in records if r["group_id"] not in protected_groups]
    labels, groups, keyed = {}, {}, []
    for r in kept:
        key = hashlib.sha256(json.dumps(r["request"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        gold = json.dumps({qid: q["gold"] for qid, q in r["supervision"].items()}, sort_keys=True)
        labels.setdefault(key, set()).add(gold)
        groups.setdefault(key, set()).add(r["group_id"])
        keyed.append((key, r))
    conflicts = {key for key, values in labels.items() if len(values) > 1}
    conflicting_groups = {g for key in conflicts for g in groups[key]}
    unique, duplicates, seen = [], [], set()
    for key, r in keyed:
        if r["group_id"] in conflicting_groups:
            continue
        if deduplicate and key in seen:
            duplicates.append(r["record_id"])
        else:
            unique.append(r)
            seen.add(key)
    return unique, {
        "before": len(records), "after": len(unique),
        "removed_record_ids": [r["record_id"] for r in records if r["group_id"] in protected_groups],
        "prior_holdout_group_ids": sorted(protected_groups),
        "conflicting_request_count": len(conflicts),
        "conflicting_label_group_ids": sorted(conflicting_groups),
        "conflicting_label_record_ids": [r["record_id"] for r in kept if r["group_id"] in conflicting_groups],
        "exact_duplicate_request_ids": duplicates,
    }
