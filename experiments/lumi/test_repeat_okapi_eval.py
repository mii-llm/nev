"""Check that paired uncertainty keeps English/Italian translations together."""
from repeat_okapi_eval import paired_changes


def check():
    current, previous = [], []
    for pair in range(4):
        for lang in ("en", "it"):
            row = {"id": f"{pair}:{lang}", "pair_id": str(pair), "family": "test", "language": lang}
            current.append({**row, "correct": lang == "it"})
            previous.append({**row, "correct": lang == "en"})
    stats = paired_changes(current, previous)
    # Every bilingual pair has zero net change; treating translations as
    # independent would incorrectly give the combined change uncertainty.
    assert stats["all"]["bootstrap_95"] == [0., 0.]
    assert stats["all"]["source_pairs"] == 4
    assert stats["en"]["accuracy_delta"] == -1.
    assert stats["it"]["accuracy_delta"] == 1.
    try:
        paired_changes(current, previous[::-1])
    except AssertionError:
        pass
    else:
        raise AssertionError("Mismatched prediction order accepted")
    print("Paired uncertainty checks passed", flush=True)


if __name__ == "__main__":
    check()
