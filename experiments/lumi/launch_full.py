"""Submit a bounded LUMI training chain only after the actual-model resume proof."""
import argparse
import json
import subprocess
import shutil
import sys
import hashlib
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, obj):
    temp = path.with_suffix(".tmp")
    with temp.open("w") as stream:
        json.dump(obj, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def launch(root, proof_job, segments, resume_empty_plan=False):
    if not proof_job.isdigit() or not 1 <= segments <= 8:
        raise ValueError("Expected a Slurm job number and 1–8 training segments")
    plan_path = root / "full-training-plan.json"
    recovering = False
    if plan_path.exists():
        old = json.loads(plan_path.read_text())
        recovering = (resume_empty_plan and old["status"] == "submitting" and
                      old["training_jobs"] == [] and old["finalization_job"] is None and old["proof_job"] == proof_job)
        if not recovering:
            raise FileExistsError("A launch plan already exists; inspect its recorded jobs before submitting anything else")
    proof_path = root / f"resume-proof-{proof_job}" / "proof.json"
    proof = json.loads(proof_path.read_text())
    if proof["status"] != "passed":
        raise ValueError("GPU resume equivalence proof has not passed")
    if proof["identity"]["manifest_sha256"] != digest(root / "data-reviewed/manifest.json"):
        raise ValueError("Data changed after GPU proof")
    if proof["identity"]["review_sha256"] != digest(root / "data-reviewed/quality-review.json"):
        raise ValueError("Review changed after GPU proof")
    repo = Path(__file__).resolve().parents[2]
    for path, expected in proof["identity"]["code_sha256"].items():
        if digest(repo / path) != expected:
            raise ValueError(f"Code changed after GPU proof: {path}")
    snapshot = root / "training-source"
    if recovering:
        for path, expected in proof["identity"]["code_sha256"].items():
            if digest(snapshot / path) != expected:
                raise ValueError("Saved source snapshot differs from the GPU proof")
    else:
        shutil.copytree(repo, snapshot, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    plan = {"status": "submitting", "mode": "full-gold", "proof_job": proof_job,
            "proof_sha256": digest(proof_path), "data_manifest_sha256": digest(root / "data-reviewed/manifest.json"),
            "training_jobs": [], "finalization_job": None, "segment_hours": 22, "max_segments": segments,
            "source_snapshot": str(snapshot)}
    atomic_json(plan_path, plan)
    # The passing proof artifact was verified above. Finished Slurm job IDs can
    # expire from dependency tracking, so only live training jobs form the chain.
    previous = None
    for _ in range(segments):
        dependency = [f"--dependency=afterok:{previous}"] if previous else []
        job = subprocess.check_output(["sbatch", "--parsable", *dependency,
              "--kill-on-invalid-dep=yes", str(snapshot / "experiments/lumi/train_full.sbatch")], universal_newlines=True).strip().split(";")[0]
        plan["training_jobs"].append(job)
        atomic_json(plan_path, plan)
        previous = job
    final = subprocess.check_output(["sbatch", "--parsable", f"--dependency=afterok:{previous}",
             "--kill-on-invalid-dep=yes", str(snapshot / "experiments/lumi/finish_full.sbatch")], universal_newlines=True).strip().split(";")[0]
    plan.update(finalization_job=final, status="submitted")
    atomic_json(plan_path, plan)
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--proof-job", required=True)
    ap.add_argument("--segments", type=int, default=8)
    ap.add_argument("--resume-empty-plan", action="store_true", help="Only after confirming a failed launch submitted zero jobs")
    a = ap.parse_args()
    launch(a.root, a.proof_job, a.segments, a.resume_empty_plan)
