"""Pinned native Laya comparison on the unchanged bilingual Okapi sample."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from okapi_eval import digest, summarize

REVISION = "fa9a2a7070b1789912a49ae24603bbfb1a78b001"
MODEL_REVISION = "e4e9ddf21a7b1903b7acffd8814ad4307bf63a67"
MAX_LEN, HEAD_MAX_LEN = 8192, 8184


def check_encoding(tok, state, question):
    """Compare native encoding byte-for-byte with its untruncated token layout."""
    from laya.common import build_sequence, render_options, serialize_state, encode_text
    q = {"t": question["type"], "ins": question["instructions"], "crit": question["criteria"]}
    assert q["t"] == "choice" and isinstance(q["ins"], str)
    encode = lambda text: encode_text(tok, text.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
    head = encode("%s question: %s" % (q["t"], q["ins"]))
    opts = [encode(" " + text) for text in render_options(q)]
    state_ids = encode(serialize_state(state))
    expected = [tok.cls_token_id] + head + [tok.sep_token_id]
    markers = []
    for opt in opts:
        markers.append(len(expected))
        expected += [tok.mask_token_id] + opt
    expected += [tok.sep_token_id] + state_ids + [tok.sep_token_id]
    actual, actual_markers = build_sequence(tok, state, q, MAX_LEN, HEAD_MAX_LEN)
    reasons = []
    if any(len(x) > 48 for x in opts):
        reasons.append("native_option_limit_48_tokens")
    if len(expected) > MAX_LEN:
        reasons.append("context_limit")
    if actual != expected or markers != actual_markers:
        if not reasons:
            reasons.append("native_head_or_state_truncation")
    elif reasons:
        raise AssertionError("Truncation audit inconsistent")
    return {"supported": not reasons, "reasons": reasons, "full_tokens": len(expected),
            "native_tokens": len(actual), "option_tokens": [len(x) for x in opts]}


def run(root, panel):
    refs = root / "references"
    sys.path.insert(0, str(refs / "laya"))
    sys.path.insert(0, str(refs / "decision-index"))
    import torch
    import laya
    from decision_index.engines import validate
    assert subprocess.check_output(["git", "-C", str(refs / "laya"), "rev-parse", "HEAD"], text=True).strip() == REVISION
    identity = json.loads((refs / "laya-model-info.json").read_text())
    assert identity["revision"] == MODEL_REVISION
    manifest = json.loads((panel / "manifest.json").read_text())
    assert digest(panel / "rows.jsonl") == manifest["rows_sha256"]
    previous = json.loads((panel / "results/report.json").read_text())
    assert previous["status"] == "complete" and previous["manifest_sha256"] == digest(panel / "manifest.json")
    out = panel / "laya-results"
    out.mkdir(exist_ok=False)
    model_dir = refs / "laya-multilingual-model"
    artifact_hashes = {name: digest(model_dir / name) for name in identity["files"] if name != ".gitattributes"}
    report = {"status": "loading", "model": identity, "code_revision": REVISION,
        "script_sha256": digest(__file__), "model_files_sha256_before_load": artifact_hashes,
        "panel_manifest_sha256": digest(panel / "manifest.json"), "checkpoint_step": manifest["checkpoint_step"],
        "budgets": {"max_len": MAX_LEN, "head_max_len": HEAD_MAX_LEN, "option_cap": 48},
        "policy": "Native Laya renderer/model and shipped temperatures; public fixed context overrides; any token truncation is unsupported and wrong in full-panel accuracy",
        "limitations": previous["limitations"] + [
            "Laya and Nesso have different architectures, training data and renderers; pretraining overlap unknown",
            "Laya uses public context/head budget overrides beyond its shipped 1024/256 defaults",
            "Common-supported accuracy excludes capacity failures and must be read with coverage"],
        "torch": torch.__version__, "gpu": torch.cuda.get_device_name()}
    save = lambda: (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    agent = laya.load(str(model_dir), device="cuda", fast=False, compile=False,
                      expected_sha256=artifact_hashes)
    assert agent.device.type == "cuda"
    report["model_files_sha256_after_load"] = {name: digest(model_dir / name) for name in artifact_hashes}
    report["temperature"] = agent.temperature
    report["numerics"] = {"parameter_dtype": str(next(agent.model.parameters()).dtype),
                           "autocast_dtype": str(agent.dtype), "amp_enabled": agent.amp_enabled}
    rows = [json.loads(x) for x in (panel / "rows.jsonl").read_text().splitlines()]
    audit = {r["id"]: check_encoding(agent.tok, r["state"], r["questions"]["q1"]) for r in rows}
    (out / "token-audit.json").write_text(json.dumps(audit, indent=2))
    report["capacity_by_cell"] = {family + "/" + lang: dict(Counter(
        "supported" if audit[r["id"]]["supported"] else ",".join(audit[r["id"]]["reasons"])
        for r in rows if r["family"] == family and r["language"] == lang))
        for family in ("MMLU", "HellaSwag", "ARC-Challenge") for lang in ("en", "it")}
    report["status"] = "running"
    save()
    print("CAPACITY", json.dumps(report["capacity_by_cell"]), flush=True)
    predictions, started = [], time.monotonic()
    with (out / "laya.jsonl").open("w") as stream:
        for i, row in enumerate(rows):
            result = {k: row[k] for k in ("id", "pair_id", "family", "language", "subject")}
            result.update(options=len(row["questions"]["q1"]["criteria"]), expected=row["expected"]["q1"])
            a = audit[row["id"]]
            if not a["supported"]:
                result.update(status="unsupported", correct=False, reasons=a["reasons"])
            else:
                # Expected answers and provenance are never passed to inference.
                response = agent.predict(row["state"], row["questions"],
                                         max_len=MAX_LEN, head_max_len=HEAD_MAX_LEN)
                validate(row["questions"], response)
                assert not response["usage"].get("truncated", False)
                answer = response["answers"]["q1"]
                result.update(status="ok", response=response, correct=answer["choice"] == result["expected"],
                    nll=-math.log(max(answer["probabilities"][result["expected"]], 1e-12)))
            predictions.append(result)
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            stream.flush()
            if (i+1) % 100 == 0 or i+1 == len(rows):
                print("LAYA", i+1, "/", len(rows), "seconds", round(time.monotonic()-started, 1), flush=True)
    assert agent.cpu_fallback_count == 0
    report["full_panel"] = {"laya": summarize(predictions), **previous["panels"]}
    supported = {r["id"] for r in predictions if r["status"] == "ok"}
    all_predictions = {"laya": predictions}
    for name in ("decision", "parent"):
        path = panel / "results" / (name + ".jsonl")
        all_predictions[name] = [json.loads(x) for x in path.read_text().splitlines()]
        assert [r["id"] for r in all_predictions[name]] == [r["id"] for r in rows]
    report["common_supported"] = {name: summarize([r for r in rs if r["id"] in supported])
                                   for name, rs in all_predictions.items()}
    # Both languages of a source pair must fit for an EN/IT matched comparison.
    by_pair = defaultdict(list)
    for row in rows:
        by_pair[(row["family"], row["pair_id"])].append(row["id"])
    paired = {uid for ids in by_pair.values() if len(ids) == 2 and set(ids) <= supported for uid in ids}
    report["bilingual_common_supported"] = {name: summarize([r for r in rs if r["id"] in paired])
                                             for name, rs in all_predictions.items()}
    report["seconds"] = time.monotonic()-started
    report["status"] = "complete"
    save()
    print("COMPLETE", json.dumps(report["full_panel"]["laya"]), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--panel", type=Path, required=True)
    a = ap.parse_args()
    run(a.root, a.panel)
