"""Prepare a paired, selection/confirmation Decision Index diagnostic on LUMI.

Reuses pinned upstream normalizers. Never trains or runs benchmark inference.
"""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

REVISION = "87d4650b42b377c0291a89c1f1a879f9b31082bf"
SEED = 20261006
CATALOG = {"ANLI": 12, "CLINC150+OOS": 5, "When2Call MCQ": 62}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def relative(path, root):
    return str(Path(path).resolve().relative_to(Path(root).resolve()))


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def normalized(text):
    return " ".join(text.casefold().split())


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def request_texts(request):
    yield from strings(request["state"])
    for question in request["questions"].values():
        yield from strings(question.get("instructions", ""))


def query_parts(row):
    if row["family"] == "When2Call MCQ":
        return [row["state"]["question"]]
    text = row["questions"]["q1"]["instructions"]
    if row["family"] == "ANLI":
        return text.split("\nPremise: ", 1)[1].split("\nHypothesis: ", 1)
    return [text.split("\n", 1)[1]]


def group(row):
    # Keep repeated premises/utterances/questions together across both panels.
    return hashlib.sha256(normalized(query_parts(row)[0]).encode()).hexdigest()


def stratum(row):
    if row["family"] == "ANLI":
        return row["split"]
    return next(iter(row["expected"].values()))


def select(rows):
    strata, used, selected = defaultdict(list), set(), []
    for row in rows:
        strata[(row["family"], stratum(row))].append(row)
    for (family, key), candidates in sorted(strata.items()):
        count = {"ANLI": 100, "CLINC150+OOS": 2, "When2Call MCQ": 100}[family]
        order = lambda r: hashlib.sha256(f"{SEED}:{r['id']}".encode()).hexdigest()
        accepted = []
        for row in sorted(candidates, key=order):
            gid = group(row)
            if gid in used:
                continue
            used.add(gid)
            accepted.append(row)
            if len(accepted) == count:
                break
        if len(accepted) != count:
            raise ValueError(f"Insufficient distinct groups: {family}/{key}")
        for i, row in enumerate(accepted):
            row = copy.deepcopy(row)
            row.update(pair_id=row["id"], language="en", panel="selection" if i % 2 == 0 else "confirmation",
                       group_id=group(row), stratum=key)
            selected.append(row)
    return selected


def technical_literal(value):
    """Protect code-like literals in prose, not ordinary schema words such as 'to'."""
    return isinstance(value, str) and not any(c.isspace() for c in value) and bool(
        re.search(r"_|[a-z][A-Z]|[a-zA-Z].*\d|\d.*[a-zA-Z]|[*/@\\]|\w\.\w", value))


def protected_names(tools):
    result = set()
    def walk(value):
        if isinstance(value, dict):
            for key, v in value.items():
                if key == "name" and technical_literal(v):
                    result.add(v)
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
    walk(tools)
    return result


def tool_call(text):
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    calls = value if isinstance(value, list) else [value]
    if calls and all(isinstance(call, dict) and "name" in call and "arguments" in call for call in calls):
        return value
    return None


def mask(text, names):
    # Protect tool identifiers and inline code, with reversible letter-only tokens.
    values = set(re.findall(r"`[^`]+`|https?://[^\s'\"<>),]+|\b\w+_\w+\b", text)) | set(names)
    values = sorted((v for v in values if v and v in text), key=lambda v: (-len(v), v))
    mapping = {}
    def token(index):
        value = ""
        while True:
            value = chr(65 + index % 26) + value
            index = index // 26 - 1
            if index < 0:
                return "__KEV_KEEP_" + value + "__"
    if "__KEV_KEEP_" in text:
        raise ValueError("Source collides with translation placeholder")
    if values:
        pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(v) for v in values) + r")(?!\w)")
        def replace(match):
            key = token(len(mapping))
            mapping[key] = match.group()
            return key
        text = pattern.sub(replace, text)
    return text, mapping


def map_request(row, translate):
    out = copy.deepcopy(row)
    names = protected_names(row["state"].get("tools", [])) if isinstance(row["state"], dict) else set()
    if row["family"] == "When2Call MCQ":
        for q in row["questions"].values():
            for text in q["criteria"].values():
                call = tool_call(text)
                if call is not None:
                    names.update(value for value in strings(call) if technical_literal(value))
    def apply(text):
        source, mapping = mask(text, names)
        value = translate(source)
        for key, original in mapping.items():
            if value.count(key) != source.count(key):
                raise ValueError("Translation changed a protected identifier")
            value = value.replace(key, original)
        return value
    if row["family"] == "When2Call MCQ":
        out["state"]["question"] = apply(row["state"]["question"])
        def descriptions(value):
            if isinstance(value, dict):
                return {k: apply(v) if k == "description" and isinstance(v, str) else descriptions(v)
                        for k, v in value.items()}
            if isinstance(value, list):
                return [descriptions(v) for v in value]
            return value
        out["state"]["tools"] = descriptions(row["state"]["tools"])
    for q in out["questions"].values():
        q["instructions"] = apply(q["instructions"])
        q["criteria"] = {k: v if row["family"] == "When2Call MCQ" and tool_call(v) is not None else apply(v)
                         for k, v in q["criteria"].items()}
    return out


def prepare(root, out):
    ref = root / "references/decision-index"
    actual = subprocess.check_output(["git", "-C", str(ref), "rev-parse", "HEAD"], text=True).strip()
    assert actual == REVISION
    if (out / "manifest.json").exists():
        raise ValueError("Prepared output already exists; use a new directory")
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ref))
    from decision_index.suite.build import acquire, adapters_added, normalize_direct
    from decision_index.suite.build.layout import Layout
    layout = Layout(out / "upstream")
    acquire.acquire(layout, [5, 12])
    adapters_added.acquire(layout, [62])
    normalize_direct.clinc150(layout)
    normalize_direct.anli(layout)
    rows = load(layout.normalized / "CLINC150+OOS.jsonl") + load(layout.normalized / "ANLI.jsonl")
    rows.extend(adapters_added.when2call(layout))
    assert Counter(r["family"] for r in rows) == {"CLINC150+OOS": 5500, "ANLI": 3200, "When2Call MCQ": 3652}
    selected = select(rows)
    assert len(selected) == 902
    # Scan only exact full fields; no claim about semantic/pretraining contamination.
    candidates = {normalized(t) for r in selected for t in query_parts(r) if len(t) >= 20}
    matches, families = [], Counter()
    train = root / "runs/bilingual-all-v1/data-reviewed/train.jsonl"
    with train.open() as stream:
        for line in stream:
            record = json.loads(line)
            families[record["source_family"]] += 1
            req = record["request"]
            if any(normalized(t) in candidates for t in request_texts(req)):
                matches.append(record["record_id"])
    save(out / "overlap-audit.json", {"exact_matches": matches, "training_sources": families})
    if matches:
        raise ValueError("Selected benchmark text overlaps training; inspect overlap-audit.json")
    jsonl(out / "english.jsonl", selected)
    texts = set()
    for row in selected:
        map_request(row, lambda text: texts.add(text) or text)
    jsonl(out / "translation-input.jsonl", [{"source": text} for text in sorted(texts)])
    checkpoints = {}
    for step, path in [(74000, root / "runs/bilingual-all-v1/decision-index-okapi-v1/checkpoint"),
                       (142000, root / "runs/bilingual-all-v1/okapi-best-review-20261006/checkpoint")]:
        target = out / "checkpoints" / str(step)
        if target.exists():
            original = {str(p.relative_to(path)): digest(p) for p in path.rglob("*") if p.is_file()}
            copied = {str(p.relative_to(target)): digest(p) for p in target.rglob("*") if p.is_file()}
            assert original == copied, "Existing checkpoint copy differs; preserve and inspect it"
        else:
            shutil.copytree(path, target)
        checkpoints[str(step)] = {str(p.relative_to(target)): digest(p) for p in target.rglob("*") if p.is_file()}
    source_files = {relative(p, out): digest(p) for p in layout.raw.rglob("*")
                    if p.is_file() and ".cache" not in p.parts}
    manifest = {"status": "awaiting_translation", "decision_index_revision": REVISION, "seed": SEED,
        "english_sha256": digest(out / "english.jsonl"), "translation_input_sha256": digest(out / "translation-input.jsonl"),
        "pairs": len(selected), "unique_translation_strings": len(texts),
        "counts": dict(Counter(r["family"] + "/" + r["panel"] for r in selected)),
        "source_gold_counts": dict(Counter(r["family"] + "/" + stratum(r) for r in rows)),
        "source_files_sha256": source_files, "checkpoint_files_sha256": checkpoints,
        "training_manifest_sha256": digest(train.parent / "manifest.json"),
        "translator": json.loads((root / "configs/translator-qwen36-35b.json").read_text()),
        "selection_rule": "Predeclared SHA256 order; 100 per ANLI round, 2 per CLINC intent, 100 per observed When2Call answer class; unique premise/query groups; alternating selection/confirmation",
        "ranking_rule": "Equal task-weighted mean of EN/IT accuracy on selection only; preserve ties, report paired uncertainty; confirmation after model choice",
        "limitations": ["Custom stratified subset, not the official Decision Index score", "Synthetic Italian needs semantic review", "Only exact training field overlap checked; pretraining contamination unknown", "CLINC OOS prevalence is intent-balanced, not the original distribution", "When2Call has four choices but only three gold classes in this pinned test source; direct answer is never gold", "Unsupported requests count as incorrect; also report matched bilingual coverage"],
        "code_sha256": {p.name: digest(p) for p in Path(__file__).parent.glob('*decision_subset*') if p.is_file()}}
    save(out / "manifest.json", manifest)
    print(dumps(manifest), flush=True)


def finalize(out):
    manifest = json.loads((out / "manifest.json").read_text())
    assert digest(out / "english.jsonl") == manifest["english_sha256"]
    assert digest(out / "translation-input.jsonl") == manifest["translation_input_sha256"]
    cache = {r["source"]: r for r in load(out / "translations.jsonl")}
    def translated(source):
        entry = cache[source]
        assert entry["translator"] == manifest["translator"]
        assert entry["error"] is None, (source, entry["error"])
        return entry["it"]
    from decision_model.schema import DecisionRequest
    rows, review = [], []
    for en in load(out / "english.jsonl"):
        it = map_request(en, translated)
        it.update(language="it")
        assert it["expected"] == en["expected"]
        for qid in en["questions"]:
            assert list(it["questions"][qid]["criteria"]) == list(en["questions"][qid]["criteria"])
        for row in (en, it):
            row["id"] = row["pair_id"] + ":" + row["language"]
            row["model"] = "nesso2"
            payload = {k: row[k] for k in ("model", "state", "questions")}
            DecisionRequest.model_validate(payload)
            row["_evaluation"] = {"run_id": "nesso-bilingual-v1:" + row["id"],
                "catalog_id": CATALOG[row["family"]], "dataset": row["family"], "track": row["stratum"],
                "group_id": row["group_id"], "language": row["language"], "panel": row["panel"],
                "pair_id": row["pair_id"], "payload_sha256": hashlib.sha256(dumps(payload).encode()).hexdigest()}
            rows.append(row)
        review.append({"pair_id": en["pair_id"], "family": en["family"], "panel": en["panel"],
                       "en": {k: en[k] for k in ("state", "questions")},
                       "it": {k: it[k] for k in ("state", "questions")}})
    hashes = {}
    for panel in ("selection", "confirmation"):
        path = out / (panel + ".jsonl")
        panel_rows = [r for r in rows if r["panel"] == panel]
        assert Counter(r["language"] for r in panel_rows) == {"en": 451, "it": 451}
        jsonl(path, panel_rows)
        hashes[panel] = digest(path)
    review.sort(key=lambda r: hashlib.sha256(r["pair_id"].encode()).hexdigest())
    sampled = [r for family in CATALOG for r in [x for x in review if x["family"] == family][:10]]
    jsonl(out / "translation-review-sample.jsonl", sampled)
    manifest.update(status="awaiting_semantic_review", panel_sha256=hashes,
                    translations_sha256=digest(out / "translations.jsonl"))
    save(out / "manifest.json", manifest)
    print("PREPARED_FOR_REVIEW", dumps(hashes), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--finalize", action="store_true")
    args = ap.parse_args()
    finalize(args.out) if args.finalize else prepare(args.root, args.out)
