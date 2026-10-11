"""Release a provisional Italian selection diagnostic; confirmation is untouched."""
import argparse
import json
from pathlib import Path

from prepare_decision_subset import digest, load, map_request, save, tool_call
from prepare_english_decision_eval import main as release
from translate_decision_subset import error

# Task-specific label corrections, reviewed against the pinned CLINC vocabulary
# and, for ambiguous meanings, its training examples. No evaluation gold used.
CLINC = {
    "account blocked": "account bloccato",
    "apr": "tasso percentuale annuo (APR)",
    "bill due": "scadenza della bolletta",
    "carry on": "bagaglio a mano",
    "change language": "cambia lingua",
    "directions": "indicazioni stradali",
    "food last": "durata di conservazione degli alimenti",
    "gas": "livello del carburante",
    "gas type": "tipo di carburante",
    "how busy": "affollamento e tempi di attesa",
    "mpg": "miglia per gallone (mpg)",
    "next holiday": "prossimo giorno festivo",
    "oil change how": "come cambiare l'olio",
    "oil change when": "quando cambiare l'olio",
    "order checks": "ordinare assegni",
    "pto balance": "saldo delle ferie e dei permessi retribuiti (PTO)",
    "pto request": "richiesta di ferie o permessi retribuiti (PTO)",
    "pto request status": "stato della richiesta di ferie o permessi retribuiti (PTO)",
    "pto used": "ferie e permessi retribuiti utilizzati (PTO)",
    "replacement card duration": "tempo di attesa per la carta sostitutiva",
    "rollover 401k": "trasferimento del piano pensionistico 401k",
    "routing": "numero di instradamento bancario",
    "smart home": "casa intelligente",
    "sync device": "sincronizzare il dispositivo",
    "text": "inviare un messaggio di testo",
    "time": "ora",
    "todo list": "lista delle cose da fare",
}


def decode(text):
    # Model output sometimes uses JSON-style quotes with literal newlines.
    # The standard decoder can handle those controls without guessing escapes.
    for _ in range(3):
        try:
            value = json.loads(text, strict=False)
        except ValueError:
            break
        if not isinstance(value, str):
            break
        text = value
    return text.strip()


def main(root, source, out):
    manifest = json.loads((source / "manifest.json").read_text())
    assert digest(source / "english.jsonl") == manifest["english_sha256"]
    cache = {r["source"]: r for r in load(source / "translations.jsonl")}
    rows, used, normalized, label_edits = [], set(), set(), 0
    english = [r for r in load(source / "english.jsonl") if r["panel"] == "selection"]
    def translate(text):
        entry = cache[text]
        assert entry["translator"] == manifest["translator"]
        assert entry["error"] is None, ("Selection translation still flagged", text)
        result = decode(entry["it"])
        assert error(text, result) is None, ("Decoded translation failed integrity checks", text)
        if result != entry["it"]:
            normalized.add(text)
        used.add(text)
        return result
    for en in english:
        it = map_request(en, translate)
        if en["family"] == "CLINC150+OOS":
            for key, label in en["questions"]["q1"]["criteria"].items():
                if label in CLINC:
                    it["questions"]["q1"]["criteria"][key] = CLINC[label]
                    label_edits += 1
        for key, question in en["questions"].items():
            for option, value in question["criteria"].items():
                if tool_call(value) is not None:
                    assert it["questions"][key]["criteria"][option] == value
        assert en["expected"] == it["expected"]
        rows.append(it)
    review = {"status": "provisional_diagnostic", "reviewer": "Codex, limited machine-assisted Italian review",
        "user_preference": "Proceed despite a few imperfect cases; do not block all scoring for minor examples",
        "scope": "Selection only; the two remaining flagged confirmation cases are not loaded or scored",
        "translations_sha256": digest(source / "translations.jsonl"),
        "shared_label_corrections": CLINC, "label_field_edits": label_edits,
        "used_unique_strings": len(used), "decoded_string_wrappers": len(normalized),
        "manual_review": "Shared 151-label CLINC vocabulary and ten sampled ANLI translations; not exhaustive",
        "limitations": ["Residual semantic errors may remain; Italian scores are provisional",
                        "One reviewed ANLI source has ambiguous negation scope; no gold labels changed",
                        "No full When2Call semantic certification; tool-call JSON is unchanged"]}
    save(out / "italian-review-details.json", review)
    release(root, source, out, language="it", translated_rows=rows, translation_review=review)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    main(args.root, args.source, args.out)
