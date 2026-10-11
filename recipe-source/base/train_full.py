"""Resumable, gold-supervised full-corpus training using Kev's actual loss/model.

One update always has equal IT/EN weight. A bounded, fixed dev sample selects
checkpoints using mean record NLL equally weighted across source/language cells.
Test and calibration records are never loaded by this trainer.
"""
import argparse
import hashlib
import json
import math
import os
import random
import signal
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import torch
import torch.nn.functional as F
from decision_model.data import digest, load_split
from decision_model.train import _encode, epoch_order, example, soft_ce


def atomic_json(path, obj):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w") as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def paired_sample(records, pairs_per_source):
    """Deterministic source-stratified sample retaining both languages per row."""
    pairs = defaultdict(list)
    for r in records:
        pairs[(r["source_family"], r["provenance"]["parallel_record"])].append(r)
    by_source = defaultdict(list)
    for (source, pair_id), pair in pairs.items():
        if Counter(r["language"] for r in pair) != {"en": 1, "it": 1}:
            raise ValueError(f"Invalid bilingual pair: {pair_id}")
        by_source[source].append((hashlib.sha256(pair_id.encode()).hexdigest(), sorted(pair, key=lambda r: r["language"])))
    return [r for source in sorted(by_source)
            for _, pair in sorted(by_source[source])[:pairs_per_source] for r in pair]


def save_state(path, model, optimizer, scheduler, progress, identity):
    """Atomic update-boundary snapshot; frozen parent is reconstructed by pinned revision."""
    state = {"format_version": 1, "identity": identity, "progress": progress,
             "parameters": {n: p.detach().cpu().clone() for n, p in model.named_parameters() if p.requires_grad},
             "optimizer": optimizer.state_dict(), "scheduler": scheduler.state_dict(),
             "torch_rng": torch.get_rng_state(),
             "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}
    path = Path(path)
    temp = path.with_suffix(".tmp")
    with temp.open("wb") as stream:
        torch.save(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def restore_state(path, model, optimizer, scheduler, identity):
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state["format_version"] != 1 or state["identity"] != identity:
        raise ValueError("Resume identity mismatch: data, recipe, dev sample or code changed")
    params = {n: p for n, p in model.named_parameters() if p.requires_grad}
    if params.keys() != state["parameters"].keys():
        raise ValueError("Resume parameter names differ")
    with torch.no_grad():
        for name, param in params.items():
            param.copy_(state["parameters"][name])
    optimizer.load_state_dict(state["optimizer"])
    scheduler.load_state_dict(state["scheduler"])
    torch.set_rng_state(state["torch_rng"])
    if state["cuda_rng"]:
        torch.cuda.set_rng_state_all(state["cuda_rng"])
    return state["progress"]


@torch.no_grad()
def evaluate(model, records, autocast):
    model.eval()
    cells, correct, questions = defaultdict(list), 0, 0
    for r in records:
        req, vecs = example(r, {}, gold_weight=1.0)
        enc = _encode(model, req)
        with autocast:
            logits = model.forward_batch([enc], form="packed")[0]
        losses = []
        for z, vec in zip(logits, vecs):
            gold = vec.index(1.0)
            losses.append(-F.log_softmax(z.float(), -1)[gold].item())
            correct += int(z.argmax().item() == gold)
            questions += 1
        cells[(r["source_family"], r["language"])].append(sum(losses) / len(losses))
    means = {"/".join(k): sum(v) / len(v) for k, v in cells.items()}
    model.train()
    return {"source_language_macro_record_nll": sum(means.values()) / len(means),
            "micro_accuracy": correct / questions, "questions": questions, "records": len(records), "cell_nll": means}


def run(args):
    from decision_model.model import DecisionModel
    root, out = args.root, args.out
    data = root / "data-reviewed"
    review = json.loads((data / "quality-review.json").read_text())
    manifest_hash = digest(data / "manifest.json")
    if review["status"] != "approved_for_training" or review["manifest_sha256"] != manifest_hash:
        raise ValueError("Missing or stale full-corpus quality review")
    cfg = json.loads((root / "base-recipe.json").read_text())
    t = cfg["train"]
    t.update(gold_weight=1.0, eval_every=2000, eval_batch=1, language_balance={"en": .5, "it": .5})
    print("Verifying and loading reviewed training data", flush=True)
    records = load_split(data, "train")
    dev = paired_sample(load_split(data, "dev"), 2 if args.smoke else 64)
    if args.smoke:
        records = paired_sample(records, 8)
        t["eval_every"] = 16
    accum = t["accumulation"]
    # Validate every language tag and balanced group before loading the GPU model.
    epoch_order(records, random.Random(0), language_balance=t["language_balance"], accumulation=accum)
    steps_per_epoch = math.ceil(len(records) / accum)
    total_steps = t["epochs"] * steps_per_epoch
    repo = Path(__file__).resolve().parents[2]
    code_files = [Path(__file__).resolve(), repo / "decision_model/train.py", repo / "decision_model/model.py",
                  repo / "decision_model/render.py", repo / "decision_model/backbones/decoder.py"]
    identity = {"manifest_sha256": manifest_hash, "review_sha256": digest(data / "quality-review.json"),
                "recipe": cfg, "train_records": len(records), "dev_record_ids": [r["record_id"] for r in dev],
                "code_sha256": {str(p.relative_to(repo)): digest(p) for p in code_files}, "smoke": args.smoke}
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = out / "latest.pt"
    config_path = out / "training_config.json"
    if config_path.exists():
        if json.loads(config_path.read_text())["identity"] != identity:
            raise ValueError("Run directory contains a different training identity")
    elif any(out.iterdir()):
        raise ValueError("Refusing a nonempty unrecognized run directory")
    atomic_json(config_path, {"identity": identity, "optimizer_steps_planned": total_steps,
        "validation": "fixed deterministic paired dev sample, 64 pairs/source; macro source/language record NLL",
        "checkpoint_every_steps": args.checkpoint_every, "mode": "gold-only"})
    torch.manual_seed(t["seed"])
    model = DecisionModel.from_parent(cfg["parent"], cfg["revision"], device="cuda",
        dtype=getattr(torch, t["weights_dtype"]), lora=t["lora"], head_dim=t["head_dim"])
    params = model.trainable_parameters()
    opt = torch.optim.AdamW(params, lr=t["lr"], weight_decay=t["weight_decay"])
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=t["lr"], total_steps=total_steps, pct_start=t["pct_start"])
    progress = {"step": 0, "records_seen": 0, "forward_tokens": 0, "wall_seconds": 0.,
                "best_nll": None, "selected_step": None, "complete": False, "dev_history": []}
    if checkpoint.exists():
        progress = restore_state(checkpoint, model, opt, sched, identity)
        print(f"Resumed optimizer, scheduler, weights and RNG at step {progress['step']}", flush=True)
    if progress["complete"]:
        atomic_json(out / "training_metrics.json", progress)
        print("Training already complete", flush=True)
        return
    stop = [False]
    for sig in (signal.SIGTERM, signal.SIGUSR1):
        signal.signal(sig, lambda *_: stop.__setitem__(0, True))
    autocast = torch.autocast("cuda", dtype=torch.bfloat16)
    start, previous_wall = time.monotonic(), progress["wall_seconds"]
    torch.cuda.reset_peak_memory_stats()
    model.train()
    opt.zero_grad(set_to_none=True)
    print(f"TRAIN {len(records)} records, {len(dev)} dev records; {total_steps} steps; 50/50 EN/IT", flush=True)

    def snapshot():
        progress["wall_seconds"] = previous_wall + time.monotonic() - start
        progress["peak_device_bytes"] = torch.cuda.max_memory_allocated()
        save_state(checkpoint, model, opt, sched, progress, identity)
        atomic_json(out / "training_metrics.json", progress)
        print(f"CHECKPOINT step={progress['step']} complete={progress['complete']}", flush=True)

    def validate():
        result = evaluate(model, dev, autocast)
        result["step"] = progress["step"]
        score = result["source_language_macro_record_nll"]
        if not math.isfinite(score):
            raise ValueError("Non-finite validation loss")
        if progress["best_nll"] is None or score < progress["best_nll"]:
            path = out / "checkpoints" / f"step-{progress['step']}"
            model.save_run(path, extra={"step": progress["step"], "recipe": t, "dev": result})
            progress.update(best_nll=score, selected_step=progress["step"], selected_path=str(path))
        progress["dev_history"].append(result)
        print("DEV " + json.dumps(result), flush=True)

    if progress["step"] == 0:
        validate()
        snapshot()
    for epoch in range(progress["step"] // steps_per_epoch, t["epochs"]):
        order = epoch_order(records, random.Random(f"{t['seed']}:epoch:{epoch}"),
                            language_balance=t["language_balance"], accumulation=accum)
        first_group = progress["step"] % steps_per_epoch
        for group_index in range(first_group, steps_per_epoch):
            batch = order[group_index * accum:(group_index + 1) * accum]
            loss_sum = 0.
            for r in batch:
                req, vecs = example(r, {}, random.Random(f"{t['seed']}:{epoch}:{r['record_id']}"), gold_weight=1.)
                enc = _encode(model, req)
                with autocast:
                    logits = model.forward_batch([enc], form="packed")[0]
                loss = sum(soft_ce(z.float(), torch.tensor(v, device=z.device)) for z, v in zip(logits, vecs)) / len(vecs)
                if not torch.isfinite(loss):
                    raise ValueError(f"Non-finite loss: {r['record_id']}")
                (loss / len(batch)).backward()
                loss_sum += loss.item()
                progress["forward_tokens"] += len(enc["ids"])
            grad_norm = torch.nn.utils.clip_grad_norm_(params, t["clip"], error_if_nonfinite=True)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            progress["step"] += 1
            progress["records_seen"] += len(batch)
            step = progress["step"]
            if step % 50 == 0 or step == 1 or args.smoke:
                print(f"STEP {step}/{total_steps} epoch={epoch} loss={loss_sum/len(batch):.5f} "
                      f"grad_norm={float(grad_norm):.4f} lr={sched.get_last_lr()[0]:.8g} "
                      f"records={progress['records_seen']} wall_s={previous_wall+time.monotonic()-start:.1f}", flush=True)
            if step % t["eval_every"] == 0 or step % steps_per_epoch == 0:
                validate()
            progress["complete"] = step == total_steps
            paused = stop[0] or time.monotonic() - start >= args.hours * 3600 or (args.stop_at and step >= args.stop_at)
            if step % args.checkpoint_every == 0 or paused or progress["complete"]:
                snapshot()
            if paused or progress["complete"]:
                print("COMPLETE" if progress["complete"] else "PAUSED at an optimizer boundary; ready to resume", flush=True)
                return


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--hours", type=float, default=22)
    ap.add_argument("--checkpoint-every", type=int, default=500)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--stop-at", type=int)
    run(ap.parse_args())
