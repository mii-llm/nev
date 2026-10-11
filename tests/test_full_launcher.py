import json
import subprocess

import pytest

from experiments.lumi import launch_full as launcher


def test_partial_submission_is_recorded_and_cannot_duplicate_jobs(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    script = repo / "experiments/lumi/launch_full.py"
    script.parent.mkdir(parents=True)
    script.write_text("# fixed source\n")
    root = tmp_path / "run"
    data = root / "data-reviewed"
    data.mkdir(parents=True)
    (data / "manifest.json").write_text("{}")
    (data / "quality-review.json").write_text("{}")
    proof_dir = root / "resume-proof-123"
    proof_dir.mkdir()
    (proof_dir / "proof.json").write_text(json.dumps({"status": "passed", "identity": {
        "manifest_sha256": launcher.digest(data / "manifest.json"),
        "review_sha256": launcher.digest(data / "quality-review.json"),
        "code_sha256": {"experiments/lumi/launch_full.py": launcher.digest(script)}}}))
    monkeypatch.setattr(launcher, "__file__", str(script))
    calls = []
    def submit(cmd, **kwargs):
        calls.append(cmd)
        if len(calls) == 2:
            raise subprocess.CalledProcessError(1, cmd)
        return "456\n"
    monkeypatch.setattr(launcher.subprocess, "check_output", submit)
    with pytest.raises(subprocess.CalledProcessError):
        launcher.launch(root, "123", 2)
    saved = json.loads((root / "full-training-plan.json").read_text())
    assert saved["training_jobs"] == ["456"]
    assert not any(arg.startswith("--dependency=") for arg in calls[0])
    assert "--dependency=afterok:456" in calls[1]
    assert (root / "training-source/experiments/lumi/launch_full.py").read_text() == script.read_text()
    with pytest.raises(FileExistsError):
        launcher.launch(root, "123", 2)
    assert len(calls) == 2
