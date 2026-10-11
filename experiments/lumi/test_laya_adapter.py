"""Run on LUMI with --root and the pinned Laya checkout/model already present."""
import argparse
import json
from pathlib import Path
import sys


def check(root):
    sys.path.insert(0, str(root / "references/laya"))
    from laya.agent import _load_tokenizer
    from laya_okapi_eval import check_encoding
    model = root / "references/laya-multilingual-model"
    tok = _load_tokenizer(str(model / "tokenizer"), json.loads((model / "rl_agent_config.json").read_text()))
    q = {"type": "choice", "instructions": "Choose the correct answer.", "criteria": {"A": "red", "B": "blue"}}
    assert check_encoding(tok, {}, q)["supported"]
    q["criteria"]["A"] = "unusually lengthy alternative " * 60
    assert "native_option_limit_48_tokens" in check_encoding(tok, {}, q)["reasons"]
    q["criteria"]["A"] = "red"
    q["instructions"] = "This is a long question. " * 100
    assert check_encoding(tok, {}, q)["supported"]
    assert not check_encoding(tok, "long state " * 10000, q)["supported"]
    print("Four native-tokenizer truncation checks passed", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    check(ap.parse_args().root)
