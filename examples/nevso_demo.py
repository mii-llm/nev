"""Experimental Nevso preview: Nev + Nesso3 on the greenhouse fixture suite.

Defaults to native CUDA serving. Pass --engine gguf for the prepared Mac CPU
runtime, or --suite /path/to/suite.json for another domain. All tools are mocks.
"""
from pathlib import Path
import runpy
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root / 'experiments' / 'cpu_gguf'
    runner = folder / 'compare_routing.py'
    sys.path.insert(0, str(folder))
    # Explicit user arguments come last and override these demo defaults.
    sys.argv = [str(runner), '--engine', 'cuda', '--suite',
                str(folder / 'greenhouse_suite.json'), *sys.argv[1:]]
    runpy.run_path(str(runner), run_name='__main__')


if __name__ == '__main__':
    main()
