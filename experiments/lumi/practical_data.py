"""Paired synthetic operational decisions with executable gold and disjoint facts.

This is a controlled rule-following diagnostic, not real customer traffic.
No teacher model, benchmark answers, or translation service is used.
"""
import hashlib
import json
import random
from collections import Counter, defaultdict


FAMILIES = ("routing", "refund", "urgency", "escalation")
LABELS = {"routing": ("billing", "delivery", "access", "general"),
          "refund": ("approve", "deny", "clarify"),
          "urgency": ("0", "1", "2"), "escalation": ("false", "true")}
SIZES = {"train": 256, "dev": 64, "calibration": 128, "test": 128}


def dumps(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha(x):
    return hashlib.sha256(dumps(x).encode()).hexdigest()


def oracle(family, f):
    if family == "routing":
        return next((k for k in f["priority"] if f[k] and
                     (k != "billing" or f["amount"] >= f["minimum"])), "general")
    if family == "refund":
        # Missing information takes precedence, even when another fact suggests rejection.
        return "clarify" if f["days"] is None or f["proof"] is None else (
            "approve" if f["days"] <= f["limit"] and f["proof"] else "deny")
    if family == "urgency":
        return "2" if f["hours"] <= f["urgent"] else "1" if f["hours"] <= f["soon"] else "0"
    return str((not f["verified"]) or f["amount"] > f["limit"] or f["attempts"] >= f["retry_limit"]).lower()


def facts(family, rng):
    if family == "routing":
        priority = ["billing", "delivery", "access"]
        rng.shuffle(priority)
        minimum = rng.randrange(1, 101)
        return {**{k: bool(rng.randrange(2)) for k in priority}, "priority": priority,
                "minimum": minimum, "amount": rng.choice([minimum-1, minimum, minimum+1])}
    if family == "refund":
        limit = rng.randrange(5, 91)
        return {"limit": limit, "days": rng.choice([None, limit-1, limit, limit+1, rng.randrange(100)]),
                "proof": rng.choice([None, False, True])}
    if family == "urgency":
        urgent = rng.randrange(1, 49)
        soon = urgent + rng.randrange(1, 100)
        return {"urgent": urgent, "soon": soon,
                "hours": rng.choice([urgent-1, urgent, urgent+1, soon, soon+1, rng.randrange(200)])}
    limit = rng.randrange(5, 1000)
    retry = rng.randrange(1, 8)
    return {"verified": bool(rng.randrange(2)), "limit": limit, "retry_limit": retry,
            "amount": rng.choice([limit-1, limit, limit+1]), "attempts": rng.randrange(9)}


def render(family, f, language, heldout=False):
    it = language == "it"
    boolean = lambda v: ("non disponibile" if it else "unavailable") if v is None else (
        ("sì" if it else "yes") if v else ("no" if it else "no"))
    if family == "routing":
        names = dict(zip(LABELS[family], ("fatturazione", "consegna", "accesso", "generale") if it
                         else ("billing", "delivery", "account access", "general")))
        order = " > ".join(names[k] for k in f["priority"])
        state = (f"Problema di fatturazione: {boolean(f['billing'])}; problema di consegna: {boolean(f['delivery'])}; "
                 f"problema di accesso: {boolean(f['access'])}; importo: {f['amount']} EUR." if it else
                 f"Billing issue: {boolean(f['billing'])}; delivery issue: {boolean(f['delivery'])}; "
                 f"account access issue: {boolean(f['access'])}; amount: {f['amount']} EUR.")
        instruction = (f"Instrada al reparto del primo problema presente in questo ordine: {order}. "
                       f"La fatturazione è ammissibile solo con un importo di almeno {f['minimum']} EUR. "
                       "Se nessun problema è ammissibile, usa generale." if it else
                       f"Route to the first issue present in this priority order: {order}. "
                       f"Billing is eligible only for an amount of at least {f['minimum']} EUR. "
                       "If no issue is eligible, use general.")
        if heldout:
            instruction = (f"Quale reparto deve ricevere il caso? In presenza di più problemi prevale quello più a sinistra "
                           f"nell'elenco {order}; escludi la fatturazione se l'importo è sotto {f['minimum']} EUR. "
                           "Se non resta nessun problema, scegli generale." if it else
                           f"Which team should receive this case? If multiple issues exist, the leftmost one in {order} wins; "
                           f"exclude billing if the amount is below {f['minimum']} EUR. If none remains, choose general.")
        return state, {"type": "choice", "instructions": instruction, "criteria": names}
    if family == "refund":
        days = ("non disponibile" if it else "unavailable") if f["days"] is None else str(f["days"])
        state = (f"Giorni dalla consegna: {days}. Prova di acquisto: {boolean(f['proof'])}." if it else
                 f"Days since delivery: {days}. Proof of purchase: {boolean(f['proof'])}.")
        instruction = (f"Prima richiedi chiarimenti se manca il numero di giorni o l'informazione sulla prova di acquisto. "
                       f"Altrimenti approva solo con prova di acquisto e al massimo {f['limit']} giorni dalla consegna; negli altri casi rifiuta." if it else
                       "First ask for clarification if either the day count or proof-of-purchase information is missing. "
                       f"Otherwise approve only with proof of purchase and at most {f['limit']} days since delivery; otherwise deny.")
        if heldout:
            instruction = (f"Decidi sul reso: il limite incluso è {f['limit']} giorni e serve una prova di acquisto. "
                           "Un requisito non soddisfatto comporta rifiuto. Tuttavia, qualsiasi dato mancante ha precedenza: chiedi chiarimenti." if it else
                           f"Decide the return: the inclusive time limit is {f['limit']} days and proof of purchase is required. "
                           "An unmet requirement means denial. However, any missing fact overrides that decision: ask for clarification.")
        labels = ("approva il rimborso", "rifiuta il rimborso", "richiedi i dati mancanti") if it else (
            "approve refund", "deny refund", "ask for missing information")
        return state, {"type": "choice", "instructions": instruction, "criteria": dict(zip(LABELS[family], labels))}
    if family == "urgency":
        state = f"Scadenza tra {f['hours']} ore." if it else f"Deadline in {f['hours']} hours."
        instruction = (f"Assegna urgenza alta se restano al massimo {f['urgent']} ore, media se restano più di "
                       f"{f['urgent']} ma al massimo {f['soon']} ore, bassa altrimenti." if it else
                       f"Assign high urgency when at most {f['urgent']} hours remain, medium when more than "
                       f"{f['urgent']} but at most {f['soon']} hours remain, and low otherwise.")
        if heldout:
            instruction = (f"Quanto è urgente? Oltre {f['soon']} ore: bassa; entro {f['urgent']} ore incluse: alta; "
                           "tra questi due intervalli: media." if it else
                           f"How urgent is this? Beyond {f['soon']} hours: low; within {f['urgent']} hours inclusive: high; "
                           "between those two ranges: medium.")
        return state, {"type": "score", "instructions": instruction,
                       "criteria": ["bassa", "media", "alta"] if it else ["low", "medium", "high"]}
    state = (f"Identità verificata: {boolean(f['verified'])}. Importo: {f['amount']} EUR. Tentativi falliti: {f['attempts']}." if it else
             f"Identity verified: {boolean(f['verified'])}. Amount: {f['amount']} EUR. Failed attempts: {f['attempts']}.")
    instruction = (f"Serve un operatore umano se l'identità non è verificata, oppure l'importo supera {f['limit']} EUR, "
                   f"oppure i tentativi falliti sono almeno {f['retry_limit']}. Negli altri casi procedi automaticamente." if it else
                   f"A human is required if identity is not verified, or the amount exceeds {f['limit']} EUR, "
                   f"or failed attempts are at least {f['retry_limit']}. Otherwise proceed automatically.")
    if heldout:
        instruction = (f"È necessario il passaggio a un operatore? L'automazione è consentita soltanto con identità verificata, "
                       f"importo non superiore a {f['limit']} EUR e meno di {f['retry_limit']} tentativi falliti." if it else
                       f"Is human handoff necessary? Automation is allowed only with verified identity, "
                       f"an amount no greater than {f['limit']} EUR and fewer than {f['retry_limit']} failed attempts.")
    return state, {"type": "noul", "instructions": instruction,
                   "criteria": {"false": "automatico" if it else "automatic", "true": "operatore umano" if it else "human operator"}}


def generate():
    result = {s: [] for s in SIZES}
    for family in FAMILIES:
        rng = random.Random("practical-v1:" + family)
        seen = set()
        for split, size in SIZES.items():
            counts = Counter()
            for index in range(size):
                wanted = LABELS[family][index % len(LABELS[family])]
                for _ in range(100000):
                    f = facts(family, rng)
                    key = sha([family, f])
                    if key not in seen and oracle(family, f) == wanted:
                        break
                else:
                    raise ValueError("Unable to construct a unique balanced case")
                seen.add(key)
                counts[wanted] += 1
                pair = "practical-v1/" + family + "/" + key
                for lang in ("en", "it"):
                    state, question = render(family, f, lang, split == "test")
                    if question["type"] == "choice":
                        keys = list(question["criteria"])
                        # Same order within a bilingual pair, independent of its answer.
                        random.Random(key).shuffle(keys)
                        question["criteria"] = {k: question["criteria"][k] for k in keys}
                    result[split].append({"record_id": pair + "/" + lang, "group_id": pair,
                        "language": lang, "source_family": "practical_" + family, "split": split,
                        "schema_family": "practical_v1." + family,
                        "request": {"state": state, "questions": {"decision": question}},
                        "supervision": {"decision": {"gold": wanted, "task": family}},
                        "provenance": {"parallel_record": pair, "facts": f, "generator": "practical-v1",
                                       "heldout_instruction_wording": split == "test"}})
    return result


def validate_pairs(splits):
    groups = {}
    for split, rows in splits.items():
        pairs = defaultdict(list)
        for r in rows:
            pairs[r["provenance"]["parallel_record"]].append(r)
            previous = groups.setdefault(r["group_id"], split)
            if previous != split:
                raise ValueError("Group crosses splits")
        for pair in pairs.values():
            if Counter(r["language"] for r in pair) != {"en": 1, "it": 1}:
                raise ValueError("Not exactly one EN and one IT record")
            if pair[0]["supervision"] != pair[1]["supervision"]:
                raise ValueError("Bilingual gold differs")
    return {s: dict(Counter(r["language"] for r in rows)) for s, rows in splits.items()}
