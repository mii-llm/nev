"""Tiny bilingual integration test through Kev's real collect/train entry points.

Not a teacher comparison or quality benchmark. Train/dev use distinct hand-written
cases; each underlying case has both languages in the same partition.
"""
import argparse
import copy
import gc
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from probe import PARENT, REVISION, records


def prepare(out):
    from decision_model.schema import DecisionRequest
    train = records()
    dev = copy.deepcopy(train)
    states = [
        ("I returned the shoes last week. Please refund them whenever convenient. There was only one charge.",
         "Ho restituito le scarpe la settimana scorsa. Rimborsatele quando possibile. C'è stato un solo addebito.", "refund", "0"),
        ("Cancel my gym membership today. All payments were correct.",
         "Annullate oggi la mia iscrizione in palestra. Tutti i pagamenti erano corretti.", "cancel", "1"),
        ("Please explain the delivery options today. There are no billing errors.",
         "Spiegatemi oggi le opzioni di consegna. Non ci sono errori di fatturazione.", "information", "1"),
        ("The app will not open. Please repair it next month; there is no rush. My bill is correct.",
         "L'app non si apre. Riparatela il prossimo mese; non ho fretta. La fattura è corretta.", "repair", "0"),
    ]
    for item in dev:
        en, it, intent, urgency = states[item["group"]]
        item["request"]["state"] = it if item["language"] == "it" else en
        item["gold"] = [intent, "false", urgency]
    manifest = {"files": {}}
    for split, items in (("train", train), ("dev", dev)):
        prepared = []
        for i, item in enumerate(items):
            DecisionRequest.model_validate(item["request"])
            prepared.append({"record_id": f"{split}/{i}", "group_id": f"{split}/case-{item['group']}",
                "source_family": "smoke_support", "schema_family": "smoke_support", "split": split,
                "language": item["language"], "request": item["request"],
                "supervision": {qid: {"gold": gold} for qid, gold in zip(item["request"]["questions"], item["gold"])},
                "provenance": {"origin": "hand-written integration examples; not a benchmark"}})
        path = out / f"{split}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in prepared))
        manifest["files"][path.name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                       "records": len(prepared), "questions": 3 * len(prepared)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher-config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    data = out / "data"
    data.mkdir()
    prepare(data)
    identity = json.loads(Path(args.teacher_config).read_text())
    cfg = {"parent": PARENT, "revision": REVISION, "data": {"out": str(data)},
           "teacher": {**identity, "out": str(out / "targets"), "dtype": "bfloat16",
                       "batch_tokens": 2048, "prompt_format": "label-chat-v1"},
           "train": {"seed": 0, "lora": {"r": 16, "alpha": 32, "dropout": .05,
                    "targets": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]},
                    "head_dim": 256, "lr": 5e-5, "weight_decay": .01, "epochs": 10,
                    "microbatch": 1, "accumulation": 8, "pct_start": .2, "clip": 1.,
                    "gold_weight": .5, "autocast": "bfloat16", "weights_dtype": "float32",
                    "activation_checkpointing": False, "eval_every": 1, "eval_batch": 2,
                    "language_balance": {"it": .5, "en": .5}, "max_steps": None}}
    (out / "recipe.json").write_text(json.dumps(cfg, indent=2) + "\n")
    import torch
    from decision_model.targets import collect, load_targets
    from decision_model.train import train
    from decision_model.model import DecisionModel
    start = time.time()
    path, meta = collect(cfg, device="cuda")
    targets = list(load_targets(path).values())
    assert len(targets) == 24 and all(t["eligible"] for t in targets), meta
    assert meta["teacher"]["parent"] == identity["model"]
    gc.collect()
    torch.cuda.empty_cache()
    metrics = train(cfg, data, path, out / "train", device="cuda")
    assert metrics["complete"] and metrics["optimizer_steps"] == 10, metrics
    model = DecisionModel.from_run(out / "train" / "selected", device="cuda")
    model.merge_lora()
    model.save_pretrained(out / "model", dtype=torch.bfloat16)
    report = {"status": "passed", "student": {"model": PARENT, "revision": REVISION}, "teacher": identity,
              "scope": "Tiny integration test only; this artifact has no validated task accuracy or calibration.",
              "train_records": {"it": 4, "en": 4}, "dev_records": {"it": 4, "en": 4},
              "gold_weight": .5, "teacher_questions": len(targets), "training": metrics,
              "wall_seconds": time.time() - start}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
