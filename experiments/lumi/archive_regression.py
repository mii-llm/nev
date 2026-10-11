"""Preserve completed comparison, reused predictions, and their integrity hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(out, job):
    report = json.loads((out / "report.json").read_text())
    assert report["status"] == "complete"
    manifest = json.loads((out / "manifest.json").read_text())
    assert report["manifest_sha256"] == sha(out / "manifest.json")
    accounting = subprocess.check_output(["sacct", "-j", str(job), "--format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList", "-P"], universal_newlines=True)
    (out / "accounting.txt").write_text(accounting)
    files = {"comparison/"+str(p.relative_to(out)): p for p in out.rglob("*")
             if p.is_file() and p.suffix in (".py", ".sbatch", ".json", ".jsonl", ".txt") and "__pycache__" not in p.parts and p.name != "archive-index.json"}
    for name, expected in manifest["baseline_sha256"].items():
        path = out.parent / name
        assert sha(path) == expected
        files["baselines/"+name] = path
    input_paths = {
        "okapi": "decision-index-okapi-v1/rows.jsonl",
        "decision_index_english": "decision-index-english-selection-v1/selection.jsonl",
        "decision_index_italian": "decision-index-italian-selection-v1/selection.jsonl",
        "practical_v2": "practical-pilot-v2/data/test.jsonl",
    }
    for name, relative in input_paths.items():
        path = out.parent / relative
        assert sha(path) == manifest["inputs"][name]
        files["inputs/" + relative] = path
    runtime = out.parent / "training-source/decision_model"
    for path in runtime.rglob("*.py"):
        files["frozen-runtime/decision_model/" + str(path.relative_to(runtime))] = path
    for name in ("artifact-sha256.json", "completion.json", "manifest.json"):
        path = out.parent / "focused-pilot-v3" / name
        if path.exists():
            files["v3-identity/" + name] = path
    task_root = out.parent.parent.parent
    log = task_root / "logs" / ("regression-v3-"+str(job)+".log")
    files["comparison/job.log"] = log
    index = {name: {"bytes": p.stat().st_size, "sha256": sha(p)} for name,p in sorted(files.items())}
    index_path = out / "archive-index.json"
    index_path.write_text(json.dumps(index,indent=2)+"\n")
    archive = out / "completed-evidence.tar.gz"
    with tarfile.open(str(archive), "w:gz") as tar:
        for name,p in sorted(files.items()):
            tar.add(str(p),arcname=name)
        tar.add(str(index_path),arcname="archive-index.json")
    print(json.dumps({"archive":str(archive),"sha256":sha(archive),"files":len(files),"accounting":accounting}))


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--job",type=int,required=True)
    a=ap.parse_args()
    main(a.out,a.job)
