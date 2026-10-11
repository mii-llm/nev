"""Small native checkpoint adapter for the upstream Decision Index runner.

Keeps the same FP32 parameters/BF16 autocast/T=1 as earlier checkpoint diagnostics.
"""
from pathlib import Path
import json
import subprocess
import sys

import torch
from decision_index.engines import Engine, Unsupported
from decision_model.model import DecisionModel
from decision_model.render import to_record
from decision_model.schema import AdmissionError, DecisionRequest


class NessoEngine(Engine):
    name = "nesso2-decision"

    def __init__(self, checkpoint, **options):
        super().__init__(checkpoint=checkpoint, **options)
        self.model = DecisionModel.from_run(checkpoint, device="cuda", dtype=torch.float32)
        self.provenance = {"checkpoint": str(checkpoint),
                           "run": json.loads((Path(checkpoint) / "run.json").read_text()),
                           "numerics": "FP32 parameters, BF16 autocast, uncalibrated T=1, native rows"}

    def __call__(self, state, questions):
        if any(q["type"] != "choice" for q in questions.values()):
            raise Unsupported("This diagnostic supports choice questions only")
        req = DecisionRequest.model_validate({"state": state, "questions": questions})
        record, meta = to_record(req)
        try:
            encoded = self.model.encode(record)
        except AdmissionError as exc:
            raise Unsupported(str(exc)) from exc
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            vectors = self.model.probs(encoded, form="rows", temperature=1.0)
        answers = {}
        for item, vector in zip(meta, vectors):
            probabilities = dict(zip(item["keys"], map(float, vector)))
            answers[item["id"]] = {"type": "choice", "choice": max(probabilities, key=probabilities.get),
                                   "probabilities": probabilities}
        return {"model": self.name, "answers": answers}, None

    def synchronize(self):
        torch.cuda.synchronize()

    def runtime(self):
        return {"torch": torch.__version__, "gpu": torch.cuda.get_device_name()}


class LayaEngine(Engine):
    name = "laya-multilingual"

    def __init__(self, root, **options):
        super().__init__(root=root, **options)
        from laya_okapi_eval import REVISION, MODEL_REVISION, MAX_LEN, HEAD_MAX_LEN, check_encoding
        from prepare_decision_subset import digest
        refs = Path(root) / "references"
        assert subprocess.check_output(["git", "-C", str(refs / "laya"), "rev-parse", "HEAD"], text=True).strip() == REVISION
        sys.path.insert(0, str(refs / "laya"))
        import laya
        info = json.loads((refs / "laya-model-info.json").read_text())
        assert info["revision"] == MODEL_REVISION
        path = refs / "laya-multilingual-model"
        hashes = {name: digest(path / name) for name in info["files"] if name != ".gitattributes"}
        self.agent = laya.load(str(path), device="cuda", fast=False, compile=False, expected_sha256=hashes)
        self.max_len, self.head_max_len = MAX_LEN, HEAD_MAX_LEN
        self.check_encoding = check_encoding
        self.provenance = {"model": info, "code_revision": REVISION, "artifact_sha256": hashes,
                           "max_len": MAX_LEN, "head_max_len": HEAD_MAX_LEN, "option_cap": 48}

    def __call__(self, state, questions):
        for question in questions.values():
            if question["type"] != "choice":
                raise Unsupported("Choice questions only")
            audit = self.check_encoding(self.agent.tok, state, question)
            if not audit["supported"]:
                raise Unsupported(",".join(audit["reasons"]))
        response = self.agent.predict(state, questions, max_len=self.max_len, head_max_len=self.head_max_len)
        assert not response["usage"].get("truncated", False)
        assert self.agent.cpu_fallback_count == 0
        return response, None

    def synchronize(self):
        torch.cuda.synchronize()
