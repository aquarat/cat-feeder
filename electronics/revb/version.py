#!/usr/bin/env python3
"""Identify design sources without circular hashes of generated PCB artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVISION = "B"


def git(*args):
    result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def identify(paths):
    """Caller lists all circuit/footprint/layout sources, never generated outputs.

    The source digest remains useful with no Git history, untracked files, or a
    dirty checkout. A Git commit alone never certifies those modified sources.
    """
    files = {}
    for path in sorted(set(Path(p).resolve() for p in paths)):
        relative = path.relative_to(ROOT).as_posix()
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not files:
        raise ValueError("Version requires explicit design source inputs")
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    source_hash = hashlib.sha256(canonical).hexdigest()
    head = git("rev-parse", "--verify", "HEAD")
    # Use the latest commit touching these inputs. Committing only generated
    # Gerbers/PCBs must not demand another silk change and an endless commit loop.
    commit = (git("log", "-1", "--format=%H", "--", *files) or head) if head else None
    changes = git("status", "--porcelain", "--untracked-files=all", "--", *files)
    dirty = (changes is None or bool(changes)) if commit else True
    short = commit[:12] if commit else None
    label = f"Rev {REVISION} / {short}{'-dirty' if dirty else ''}" if short else f"Rev {REVISION} / src-{source_hash[:12]}"
    return {
        "hardware_revision": REVISION,
        "silkscreen_identifier": label,
        "git_commit": commit,
        "git_short": short,
        "design_sources_dirty": dirty,
        "source_sha256": source_hash,
        "source_files_sha256": files,
        "scope": "Source identity, not fabrication or physical qualification. Generated artifact hashes are separate.",
    }


def write(paths, output=None):
    record = identify(paths)
    target = Path(output) if output else HERE / "version.json"
    target.write_text(json.dumps(record, indent=2) + "\n")
    return record
