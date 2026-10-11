"""Journal one CPU preparation and one dependent GPU pilot; safe to repeat."""
import argparse
import json
import os
import subprocess
from pathlib import Path


def save(path, value):
    temp = path.with_suffix(".tmp")
    with temp.open("w") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(temp), str(path))


def main(out):
    journal = out / "jobs.json"
    jobs = json.loads(journal.read_text()) if journal.exists() else {
        "experiment": "focused-pilot-v3", "prepare": None, "pilot": None,
        "scope": "Targeted 50/50 intent/routing adaptation from v2; <=1024 updates, two retention guards, Laya test comparison and private export"}
    if jobs["experiment"] != "focused-pilot-v3":
        raise ValueError("Different experiment already occupies this directory")
    save(journal, jobs)
    if jobs["prepare"] is None:
        jobs["prepare"] = subprocess.check_output(["sbatch", "--parsable", str(out / "source/prepare_focused_v3.sbatch"), str(out)],
                                                  universal_newlines=True).strip().split(";")[0]
        save(journal, jobs)
    if jobs["pilot"] is None:
        jobs["pilot"] = subprocess.check_output(["sbatch", "--parsable", "--dependency=afterok:" + jobs["prepare"],
            "--kill-on-invalid-dep=yes", str(out / "source/focused_v3.sbatch"), str(out)],
            universal_newlines=True).strip().split(";")[0]
        save(journal, jobs)
    print(json.dumps(jobs))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    main(ap.parse_args().out)
