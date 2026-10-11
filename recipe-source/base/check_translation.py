"""Inspect an alternative translator on observed failures before corpus use."""
import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from bilingual_data import translation_messages, translation_error

ap = argparse.ArgumentParser()
ap.add_argument("--root", type=Path, required=True)
ap.add_argument("--identity", type=Path, required=True)
args = ap.parse_args()
identity = json.loads(args.identity.read_text())
tok = AutoTokenizer.from_pretrained(identity["model"], revision=identity["revision"], padding_side="left")
model = AutoModelForCausalLM.from_pretrained(identity["model"], revision=identity["revision"], dtype=torch.bfloat16).to("cuda").eval()
texts = [
    'Hypothesis: "Never eat french fries under any circumstances." How does it relate to the premise?',
    "The hypothesis may or may not be true given the premise",
    "The hypothesis follows from the premise",
    "The hypothesis contradicts the premise",
    "Its clean interior is surprisingly plain, but it once held the remains of Christopher Columbus.",
    "the genius of the work speaks volumes , offering up a hallucinatory dreamscape that frustrates and captivates .",
    "Staying, or leaving not mentioned", "The rain jacket you sent is a men's medium. I ordered the women's medium.",
    "I was not charged twice. I need to cancel my membership, but not before next month.",
    "What country is Kosovo a part of ?", "When was Lyndon B. Johnson born ?",
    "Deliveries up to 3 days after the promised date count as on time. Deliveries 4 to 10 days after it are a minor delay and earn a shipping refund. Later deliveries are a major delay and earn a full refund.",
    "Approve only if the balance is at least 30 and the request has not expired.",
    "Do you support the exchange of EUR from my currency.",
    "The bill is £64.00.",
]
rows = []
for start in range(0, len(texts), 8):
    part = texts[start:start + 8]
    prompts = [tok.apply_chat_template(translation_messages(s), tokenize=False, add_generation_prompt=True, enable_thinking=False) for s in part]
    inputs = tok(prompts, padding=True, add_special_tokens=False, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        outputs = model.generate(**inputs, do_sample=False, max_new_tokens=256, pad_token_id=tok.pad_token_id)
    for s, ids in zip(part, outputs[:, inputs.input_ids.shape[1]:]):
        it = tok.decode(ids, skip_special_tokens=True).strip()
        row = {"source": s, "it": it, "error": translation_error(s, it)}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
(args.root / "alternative-translation-check.json").write_text(json.dumps({"identity": identity, "rows": rows}, indent=2, ensure_ascii=False))
