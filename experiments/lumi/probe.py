"""Bounded Nesso2/ROCm compatibility probe, not a quality benchmark.

Uses Kev's real head/execution code with an explicit Llama load and a process-local
delimiter override. Production backend dispatch and artifact export remain future work.
"""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PARENT = "mii-llm/nesso2-0.4B-agentic"
REVISION = "86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041"
DELIMITERS = tuple(f"<|reserved_special_token_{i}|>" for i in range(5))


def records():
    pairs = [
        ("I was charged twice. Please refund the duplicate today.",
         "Mi avete addebitato due volte. Rimborsate oggi il doppio addebito.", "refund", "true", "1"),
        ("Please cancel my subscription at the end of next month. I was charged correctly.",
         "Annullate il mio abbonamento alla fine del prossimo mese. Gli addebiti sono corretti.", "cancel", "false", "0"),
        ("What are your opening hours? There is no rush and no problem with my payments.",
         "Quali sono i vostri orari di apertura? Non ho fretta e i pagamenti sono corretti.", "information", "false", "0"),
        ("My router stopped working. Please fix it today. My payments are correct.",
         "Il router non funziona più. Riparatelo oggi. I pagamenti sono corretti.", "repair", "false", "1"),
    ]
    out = []
    for group, (en, it, intent, duplicate, urgency) in enumerate(pairs):
        for lang, state in (("en", en), ("it", it)):
            italian = lang == "it"
            out.append({
                "group": group, "language": lang,
                "request": {"state": state, "questions": {
                    "intent": {"type": "choice", "instructions": "Qual è la richiesta principale?" if italian else "What is the main request?",
                               "criteria": dict(zip(("refund", "cancel", "information", "repair"),
                                   ("Rimborso", "Annullamento", "Informazioni", "Riparazione") if italian else
                                   ("Refund", "Cancellation", "Information", "Repair")))},
                    "duplicate": {"type": "noul", "instructions": "Il cliente segnala un doppio addebito?" if italian else "Does the customer report a duplicate charge?"},
                    "urgency": {"type": "score", "instructions": "Valuta la scadenza richiesta." if italian else "Rate the requested deadline.",
                                "criteria": ["Non urgente", "Oggi"] if italian else ["Not urgent", "Today"]},
                }},
                "gold": [intent, duplicate, urgency],
            })
    return out


def run(args, report):
    import torch
    import torch.nn.functional as F
    import peft
    import transformers
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModel, AutoTokenizer
    import decision_model.render as renderer
    from decision_model.model import DecisionModel, PointerHead
    from decision_model.schema import DecisionRequest
    from decision_model.targets import ParentScorer

    assert torch.cuda.is_available(), "Run inside a Slurm GPU allocation"
    assert torch.version.hip, "This experiment is intended for LUMI ROCm"
    torch.manual_seed(0)
    torch.set_num_threads(4)
    report.update(versions={"torch": torch.__version__, "transformers": transformers.__version__, "peft": peft.__version__, "hip": torch.version.hip},
                  device=torch.cuda.get_device_name(0), parent=PARENT, revision=REVISION,
                  scope="Compatibility and gradients only; eight hand-written paired examples; no held-out accuracy estimate.")
    tok = AutoTokenizer.from_pretrained(PARENT, revision=REVISION, local_files_only=True)
    if not args.integrated:
        renderer.SPECIAL = DELIMITERS  # Legacy exploratory probe, only in this process.
    ids = renderer.delimiter_ids(tok)
    assert len(set(ids.values())) == 5
    assert all(tok.encode(t, add_special_tokens=False) == [i] for t, i in zip(DELIMITERS, ids.values()))
    assert not set(renderer.user_tokens(tok, " ".join(DELIMITERS))) & set(ids.values())
    report["delimiters"] = ids
    print("Tokenizer and delimiter checks passed", flush=True)
    scorer = ParentScorer(PARENT, REVISION, device="cpu", load_model=False)
    sample = records()
    for item in sample:
        plan = scorer.plan(DecisionRequest.model_validate(item["request"]), "cyclic")
        assert all(p["reason"] is None for p in plan), plan
    report["teacher_label_boundaries"] = "passed for both languages and all three question types"

    lora = {"r": 16, "alpha": 32, "dropout": 0.05,
            "targets": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]}
    if args.integrated:
        model = DecisionModel.from_parent(PARENT, REVISION, device="cuda", lora=lora)
    else:
        lm, info = AutoModel.from_pretrained(PARENT, revision=REVISION, local_files_only=True,
            dtype=torch.float32, attn_implementation="sdpa", output_loading_info=True)
        assert lm.config.model_type == "llama" and not info["missing_keys"], info
        lm.requires_grad_(False)
        lm = get_peft_model(lm, LoraConfig(task_type="FEATURE_EXTRACTION", r=16, lora_alpha=32,
            lora_dropout=0.05, target_modules=lora["targets"]))
        model = DecisionModel(tok, lm, PointerHead(lm.config.hidden_size, 256), "cuda",
                              parent={"name": PARENT, "revision": REVISION}, lora=lora)
    report["integrated_api"] = args.integrated
    report["trainable_parameters"] = sum(p.numel() for p in model.trainable_parameters())
    encoded, golds = [], []
    for item in sample:
        rec, meta = renderer.to_record(DecisionRequest.model_validate(item["request"]))
        encoded.append(model.encode(rec))
        golds.append([m["keys"].index(g) for m, g in zip(meta, item["gold"])])
    report["examples"] = {"it": 4, "en": 4, "questions_each": 3,
                          "packed_tokens": {lang: sum(len(e["ids"]) for e, r in zip(encoded, sample) if r["language"] == lang) for lang in ("it", "en")}}

    def parity():
        model.eval()
        deltas = []
        for enc in encoded[:2]:
            ref = model.probs(enc, form="packed")
            for form in ("rows", "cached"):
                ps = model.probs(enc, form=form)
                d = max((a-b).abs().max().item() for a, b in zip(ref, ps))
                deltas.append({"form": form, "max_abs_dp": d})
                assert d < 1e-4, deltas
        # Added questions must not influence earlier branches.
        rec, _ = renderer.to_record(DecisionRequest.model_validate(sample[0]["request"]))
        solo = model.encode({"state": rec["state"], "questions": rec["questions"][:1]})
        d = (model.probs(solo, form="packed")[0] - model.probs(encoded[0], form="packed")[0]).abs().max().item()
        assert d < 1e-4, d
        return {"comparisons": deltas, "question_isolation_max_abs_dp": d}

    report["parity_before"] = parity()
    print("Packed/rows/cached and isolation checks passed", flush=True)
    opt = torch.optim.AdamW(model.trainable_parameters(), lr=5e-5, weight_decay=0.01)
    report["losses"] = []
    report["objective"] = "Gold-only diagnostic; independent-teacher experiment follows separately"
    for step in range(args.steps):
        model.train()
        opt.zero_grad(set_to_none=True)
        total = 0.0
        # Exactly four IT + four EN records per optimizer update.
        for enc, gs in zip(encoded, golds):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                zs = model.forward_batch([enc], form="packed")[0]
                loss = sum(-F.log_softmax(z.float(), -1)[g] for z, g in zip(zs, gs)) / len(gs)
            assert torch.isfinite(loss), loss
            (loss / len(encoded)).backward()
            total += loss.item() / len(encoded)
        if step == 0:
            grads = {kind: sum(float(p.grad.float().square().sum()) for name, p in model.named_parameters()
                               if p.grad is not None and kind in name) ** 0.5 for kind in ("lora_", "head.")}
            assert all(v > 0 and v < float("inf") for v in grads.values()), grads
            report["first_gradient_norms"] = grads
        torch.nn.utils.clip_grad_norm_(model.trainable_parameters(), 1.0)
        opt.step()
        report["losses"].append(total)
        print(json.dumps({"step": step + 1, "loss": total}), flush=True)
    report["parity_after"] = parity()
    if args.integrated:
        def predictions(m):
            return [p for enc in encoded[:2] for p in m.probs(enc, form="cached")]

        def delta(a, b):
            return max((x-y).abs().max().item() for x, y in zip(a, b))

        ref = predictions(model)
        model.save_run(Path(args.out) / "checkpoint")
        restored = DecisionModel.from_run(Path(args.out) / "checkpoint", device="cuda")
        run_delta = delta(ref, predictions(restored))
        assert run_delta < 1e-5, run_delta
        restored.merge_lora()
        merge_delta = delta(ref, predictions(restored))
        assert merge_delta < 1e-4, merge_delta
        restored.save_pretrained(Path(args.out) / "model", dtype=torch.bfloat16)
        deployed = predictions(restored)
        reloaded = DecisionModel.from_pretrained(Path(args.out) / "model", device="cuda")
        reload_delta = delta(deployed, predictions(reloaded))
        assert reload_delta < 1e-3, reload_delta
        assert reloaded.lm.config.model_type == "llama" and reloaded.lm.config.num_hidden_layers == 32
        report["roundtrip"] = {"run_max_abs_dp": run_delta, "merge_max_abs_dp": merge_delta,
                               "bf16_reload_max_abs_dp": reload_delta,
                               "artifact": "Diagnostic only; not validated for deployment"}
        print("Run, merge and BF16 artifact reload checks passed", flush=True)
    report["peak_gpu_allocated_bytes"] = torch.cuda.max_memory_allocated()
    report["status"] = "passed"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--integrated", action="store_true", help="Use the supported loader and test artifact round trips")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    report = {"status": "running"}
    start = time.time()
    try:
        run(args, report)
    except Exception:
        report.update(status="failed", traceback=traceback.format_exc())
        raise
    finally:
        report["wall_seconds"] = time.time() - start
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
