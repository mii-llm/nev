"""Audit selected checkpoint precision, updates, and ability to memorize clean pairs.

The eight-example overfit test is deliberately diagnostic, never a quality score.
No held-out test data controls these checks.
"""
import argparse
import contextlib
import copy
import gc
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from decision_model.data import load_split, write_json, write_jsonl
from decision_model.model import DecisionModel
from decision_model.render import delimiter_ids, to_record
from decision_model.schema import DecisionRequest
from decision_model.train import example, soft_ce
from probe import records as toy_records
from run_bilingual_pilot import summarize, model_rows


def main(root, out):
    import torch
    out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(4)
    cfg = json.loads((root / "gold" / "recipe.json").read_text())
    report = {"status": "running", "scope": "Training diagnostics; no quality claim from memorization", "checks": {}}
    start = time.monotonic()
    def save():
        report["wall_seconds"] = time.monotonic() - start
        write_json(out / "report.json", report)
    # A deterministic source/language-stratified training sample, not held-out tests.
    counts = Counter()
    sample = []
    for r in load_split(root / "data", "train"):
        cell = r["source_family"], r["language"]
        if counts[cell] < 4:
            sample.append(r); counts[cell] += 1
    write_jsonl(out / "training-sample.jsonl", sample)
    selected = DecisionModel.from_run(root / "gold/train/selected", device="cuda")
    with torch.inference_mode():
        raw = model_rows(selected, sample)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            mixed = model_rows(selected, sample)
        enc = selected.encode(to_record(DecisionRequest.model_validate(sample[0]["request"]))[0])
        packed = selected.probs(enc, form="packed", temperature=1)
        parity = {f: max(float((a-b).abs().max()) for a,b in zip(packed,selected.probs(enc,form=f,temperature=1))) for f in ("rows","cached")}
    def compare(a,b):
        assert [(r["record_id"],r["qid"],r["keys"]) for r in a] == [(r["record_id"],r["qid"],r["keys"]) for r in b]
        return {"max_abs_probability_delta": max(abs(x-y) for r,s in zip(a,b) for x,y in zip(r["probs"],s["probs"])),
                "argmax_changes": sum(max(range(len(r["probs"])),key=r["probs"].__getitem__) != max(range(len(s["probs"])),key=s["probs"].__getitem__) for r,s in zip(a,b))}
    report["checks"]["selected_train_sample"] = {"fp32": summarize(raw), "bf16_autocast": summarize(mixed),
              "precision_delta": compare(raw,mixed), "execution_form_deltas": parity}
    assert all(v < 1e-4 for v in parity.values()), parity
    del selected
    gc.collect(); torch.cuda.empty_cache()
    exported = DecisionModel.from_pretrained(root / "gold/model", device="cuda")
    deployed = model_rows(exported,sample)
    report["checks"]["selected_train_sample"].update(export_bf16=summarize(deployed), export_delta=compare(raw,deployed))
    del exported
    gc.collect(); torch.cuda.empty_cache()
    save()
    print("Precision and execution-form audit completed", flush=True)
    toys = []
    for i,r in enumerate(toy_records()):
        toys.append({"record_id":f"overfit/{i}", "group_id":f"overfit/{r['group']}", "language":r["language"],
             "source_family":"diagnostic_support", "request":r["request"],
             "supervision":{qid:{"gold":g} for qid,g in zip(r["request"]["questions"],r["gold"])}})
    write_jsonl(out / "overfit-records.jsonl", toys)
    report["overfit"] = {}
    for lr in (5e-5, 5e-4):
        torch.manual_seed(0)
        model = DecisionModel.from_parent(cfg["parent"],cfg["revision"], device="cuda", lora=cfg["train"]["lora"])
        params = dict((n,p) for n,p in model.named_parameters() if p.requires_grad)
        assert sum(p.numel() for p in params.values()) == 9175552
        assert all("lora_" in n or n.startswith("head.") for n in params)
        before = {n:p.detach().cpu().clone() for n,p in params.items()}
        emb = model.lm.get_input_embeddings().weight.detach()
        d = delimiter_ids(model.tok)
        vectors = emb[torch.tensor(list(d.values()),device=emb.device)].float()
        report["checks"]["delimiters"] = {"ids":d,"embedding_norms":vectors.norm(dim=1).tolist(),
             "pairwise_distance":torch.cdist(vectors,vectors).tolist(),
             "ordinary_embedding_norms":emb[torch.tensor(model.tok.encode("hello ciao refund annullamento",add_special_tokens=False),device=emb.device)].float().norm(dim=1).tolist()}
        opt = torch.optim.AdamW(list(params.values()),lr=lr,weight_decay=.01)
        arm = {"lr":lr,"schedule":"constant for bounded memorization diagnostic", "history":[],"gradient_checks":[]}
        report["overfit"][str(lr)] = arm
        for step in range(201):
            if step % 25 == 0:
                model.eval()
                rows = model_rows(model,toys)
                s=summarize(rows)
                arm["history"].append({"step":step,"accuracy":s["overall"]["accuracy"],"nll":s["overall"]["nll"],"by_language":s["by_language"]})
                print("overfit",lr,step,"accuracy",s["overall"]["accuracy"],"nll",s["overall"]["nll"],flush=True)
                save()
                if s["overall"]["accuracy"] == 1 and s["overall"]["nll"] < .05:
                    break
            if step == 200:
                break
            model.train(); opt.zero_grad(set_to_none=True)
            for r in toys:
                req, targets = example(r, {}, random.Random(f"{step}:{r['record_id']}"),gold_weight=1)
                enc=model.encode(to_record(req)[0])
                with torch.autocast("cuda",dtype=torch.bfloat16):
                    zs=model.forward_batch([enc],form="packed")[0]
                loss=sum(soft_ce(z.float(),torch.tensor(t,device=z.device)) for z,t in zip(zs,targets))/len(zs)
                assert torch.isfinite(loss)
                (loss/len(toys)).backward()
            if step in (0,1,24,99):
                by_kind=defaultdict(float)
                for name,p in params.items():
                    if p.grad is not None:
                        assert torch.isfinite(p.grad).all(),name
                        kind="head" if name.startswith("head.") else "lora_A" if "lora_A" in name else "lora_B"
                        by_kind[kind]+=p.grad.float().square().sum().item()
                norms={k:v**.5 for k,v in by_kind.items()}
                assert norms["head"]>0 and norms["lora_B"]>0
                if step>0: assert norms["lora_A"]>0
                arm["gradient_checks"].append({"step":step,"norms":norms})
            torch.nn.utils.clip_grad_norm_(list(params.values()),1)
            opt.step()
        deltas=defaultdict(float)
        changed=Counter()
        for name,p in params.items():
            delta=p.detach().cpu()-before[name]
            kind="head" if name.startswith("head.") else "lora"
            deltas[kind]+=delta.square().sum().item()
            changed[kind]+=int(bool(delta.ne(0).any()))
        arm["parameter_updates"]={"delta_norms":{k:v**.5 for k,v in deltas.items()},"changed_tensors":dict(changed)}
        assert all(v>0 for v in deltas.values()),"Optimizer did not update both head and adapters"
        arm["memorized"] = arm["history"][-1]["accuracy"] >= .95
        save()
        del model, opt, params, before, vectors, emb
        gc.collect(); torch.cuda.empty_cache()
    report["status"]="complete"
    save()


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); main(a.root,a.out)
