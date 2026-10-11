import copy
import random

import pytest
import torch

from experiments.lumi.train_full import paired_sample, restore_state, save_state
from decision_model.train import epoch_order
from experiments.lumi.review_full import correct_schema, untranslated_hypothesis
from collections import Counter


def make():
    torch.manual_seed(7)
    model = torch.nn.Sequential(torch.nn.Linear(5, 8), torch.nn.Dropout(.3), torch.nn.Linear(8, 2))
    opt = torch.optim.AdamW(model.parameters(), lr=.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=.01, total_steps=20)
    return model, opt, sched


def updates(model, opt, sched, n):
    for _ in range(n):
        y = model(torch.ones(3, 5)).square().mean()
        y.backward()
        opt.step()
        sched.step()
        opt.zero_grad(set_to_none=True)


def test_optimizer_scheduler_and_dropout_resume_exactly(tmp_path):
    model, opt, sched = make()
    updates(model, opt, sched, 20)
    expected = copy.deepcopy(model.state_dict())
    model, opt, sched = make()
    updates(model, opt, sched, 7)
    save_state(tmp_path / "latest.pt", model, opt, sched, {"step": 7}, {"data": "pinned"})
    model, opt, sched = make()
    p = restore_state(tmp_path / "latest.pt", model, opt, sched, {"data": "pinned"})
    assert p["step"] == 7 and sched.last_epoch == 7
    updates(model, opt, sched, 13)
    assert all(torch.equal(v, expected[k]) for k, v in model.state_dict().items())
    with pytest.raises(ValueError, match="identity"):
        restore_state(tmp_path / "latest.pt", model, opt, sched, {"data": "changed"})


def test_partial_epoch_resumes_without_skips_or_duplicates_and_stays_balanced():
    rows = [{"record_id": f"{i}/{lang}", "language": lang, "source_family": "x",
             "provenance": {"parallel_record": str(i)}} for i in range(11) for lang in ("en", "it")]
    order = epoch_order(rows, random.Random("0:epoch:0"), language_balance={"it": .5, "en": .5}, accumulation=8)
    resumed = epoch_order(rows, random.Random("0:epoch:0"), language_balance={"it": .5, "en": .5}, accumulation=8)[8:]
    assert order[:8] + resumed == order
    assert len({r["record_id"] for r in order}) == len(rows)
    for start in range(0, len(order), 8):
        count = Counter(r["language"] for r in order[start:start+8])
        assert count["en"] == count["it"]
    assert paired_sample(rows, 3) == paired_sample(list(reversed(rows)), 3)
    assert len(paired_sample(rows, 3)) == 6


def test_review_fixes_exact_text_preserving_keys_and_flags_untranslated_hypothesis():
    en = {"criteria": {"returns": "returns", "entailment": "entailment"}}
    it = {"criteria": {"returns": "residui", "entailment": "entailment"}}
    fixed = correct_schema(en, it, Counter())
    assert fixed == {"criteria": {"returns": "resi", "entailment": "implicazione"}}
    a = {"source_family": "mnli", "request": {"questions": {"relation": {"instructions": 'Hypothesis: "The report contains no information" How does it relate?'}}}}
    b = copy.deepcopy(a)
    b["request"]["questions"]["relation"]["instructions"] = 'Ipotesi: "The report contains no information" Come si relaziona?'
    assert untranslated_hypothesis(a, b)
    b["request"]["questions"]["relation"]["instructions"] = 'Ipotesi: "Il rapporto non contiene informazioni" Come si relaziona?'
    assert not untranslated_hypothesis(a, b)
