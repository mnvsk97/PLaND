#!/usr/bin/env python3
"""Offline code, saved-evidence and current-manuscript checks. No model calls."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('paper_audit', ROOT / 'paper/audit_paper.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_directories():
    roots = ('datasets', 'experiments', 'skills', '.codex/skills', 'paper')
    return sorted({path.parent for folder in roots for path in (ROOT / folder).rglob('test_*.py')})


def main():
    directories = test_directories()
    for directory in directories:
        print(f'TEST {directory.relative_to(ROOT)}', flush=True)
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(directory), '-p', 'test_*.py', '-v'], cwd=ROOT, check=True)
    evidence = AUDIT.verify_index(AUDIT.OUT / 'evidence-files.json')
    paper = AUDIT.verify_index(AUDIT.OUT / 'paper-artifacts.json')
    # The complete statistical audit has its own entry point; verify all of its
    # inputs here and run it explicitly before release. No stale historical
    # summary is treated as a current manuscript result.
    subprocess.run([sys.executable, 'paper/audit_paper.py', '--artifacts'], cwd=ROOT, check=True)
    print(f'PASS: {len(directories)} test directories; {evidence} frozen evidence/code files; {paper} manuscript files.', flush=True)


if __name__ == '__main__':
    main()
