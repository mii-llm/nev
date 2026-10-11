"""Translate Kev's text values through the user's local LUMI vLLM server."""
import argparse
import hashlib
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bilingual_data import (SPLITS, load_split, normalize_request, translate_request,
                            translation_error, translation_messages)

PREFLIGHT = [
    'Hypothesis: "Never eat french fries under any circumstances." How does it relate to the premise?',
    "The hypothesis may or may not be true given the premise",
    "The hypothesis follows from the premise", "The hypothesis contradicts the premise",
    "the genius of the work speaks volumes , offering up a hallucinatory dreamscape that frustrates and captivates .",
    "Staying, or leaving not mentioned",
    "I was not charged twice. I need to cancel my membership, but not before next month.",
    "What country is Kosovo a part of ?", "When was Lyndon B. Johnson born ?",
    "Approve only if the balance is at least 30 and the request has not expired.", "The bill is £64.00.",
]
PROMPT_VERSION = "vllm-quoted-fewshot-v3"


def main(args):
    identity = json.loads(args.identity.read_text())
    texts = set()
    for split in SPLITS:
        for r in load_split(args.root / "english", split):
            if r["source_family"] != "composition":
                translate_request(normalize_request(r["request"]), lambda s: texts.add(s) or s)
    cache_file = args.root / f"translations-{PROMPT_VERSION}.jsonl"
    cache = {r["source"]: r for r in map(json.loads, cache_file.read_text().splitlines())} if cache_file.exists() else {}
    assert all(r["translator"] == identity for r in cache.values()), "Cache model mismatch"

    def translate(source):
        messages = translation_messages(source)
        budget = min(4096, max(256, len(source) // 2 + 256))
        for attempt in range(3):
            body = {"model": args.model, "messages": messages, "temperature": 0, "top_p": 1,
                    "max_tokens": budget, "seed": int(hashlib.sha256(source.encode()).hexdigest()[:8], 16) % 2147483647,
                    "chat_template_kwargs": {"enable_thinking": False}}
            request = urllib.request.Request(args.base_url.rstrip("/") + "/chat/completions",
                        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    data = json.load(response)
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
                continue
            choice = data["choices"][0]
            translated = (choice["message"].get("content") or "").strip()
            error = translation_error(source, translated)
            if choice["finish_reason"] != "stop":
                error = "incomplete_generation:" + str(choice["finish_reason"])
            if error and attempt < 2:
                messages = translation_messages(source)
                messages[0]["content"] += (" IMPORTANT: keep every numeral in digits with its original separators. "
                    "Keep exactly the original number of question marks. Translate the entire text, never answer it.")
                budget = min(4096, budget * 2)
                continue
            return {"source": source, "it": translated, "error": error, "translator": identity,
                    "prompt_version": PROMPT_VERSION, "usage": data.get("usage"), "attempts": attempt + 1}

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        preflight = list(pool.map(translate, PREFLIGHT))
        (args.root / "vllm-translation-preflight.json").write_text(json.dumps(preflight, indent=2, ensure_ascii=False) + "\n")
        for row in preflight:
            print(json.dumps(row, ensure_ascii=False), flush=True)
        assert all(r["error"] is None for r in preflight), "Translation preflight failed; inspect saved outputs"
        pending = sorted(texts - {s for s, r in cache.items() if not r["error"]})
        started = time.time()
        print(f"vLLM translation: {len(texts)} unique strings; {len(pending)} pending", flush=True)
        futures = {pool.submit(translate, s): s for s in pending}
        with cache_file.open("a") as stream:
            for i, future in enumerate(as_completed(futures), 1):
                row = future.result()
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                cache[row["source"]] = row
                if i % 100 == 0 or i == len(pending):
                    print(f"vLLM translation: {i}/{len(pending)}, {time.time() - started:.0f}s, "
                          f"flagged {sum(bool(r['error']) for r in cache.values())}", flush=True)
    assert texts <= set(cache)
    print("Translation cache complete: " + str(cache_file), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--identity", type=Path, required=True)
    ap.add_argument("--base-url", default="http://127.0.0.1:8017/v1")
    ap.add_argument("--model", default="Qwen3.6-35B-A3B")
    ap.add_argument("--concurrency", type=int, default=32)
    main(ap.parse_args())
