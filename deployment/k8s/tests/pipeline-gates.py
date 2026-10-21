"""Run the ref/digest gate steps of k3s-pipeline.yml with bash under each input combination.

Each step's `run:` script is executed exactly as written in the workflow, with its `env:` values
replaced by the case's values. Exit 0 = gate passes, non-zero = gate refuses.
Usage: python3 deployment/k8s/tests/pipeline-gates.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/k3s-pipeline.yml"
DIGEST = "ghcr.io/spacemanspiff99/issue-tracker@sha256:" + "a" * 64
OTHER = "ghcr.io/spacemanspiff99/issue-tracker@sha256:" + "b" * 64
MAIN, BRANCH = "refs/heads/main", "refs/heads/feature"


def gate(job: str) -> dict:
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"][job]["steps"]
    return next(s for s in steps if s.get("name", "").startswith("Require main"))


def run(job: str, env: dict[str, str], image: str) -> bool:
    """Run the job's gate step. IMAGE comes from the job-level env in the workflow."""
    step = gate(job)
    assert set(step["env"]) == set(env), (job, sorted(step["env"]), sorted(env))
    proc_env = {"PATH": "/usr/bin:/bin", **env, "IMAGE": image}
    return subprocess.run(["bash", "-e", "-c", step["run"]], env=proc_env).returncode == 0


def uat(ref: str, allow: bool, promote: bool, expected: str, image: str = DIGEST) -> bool:
    env = {"REF": ref, "ALLOW": str(allow).lower(), "PROMOTE": str(promote).lower(), "EXPECTED": expected}
    return run("deploy-uat", env, image)


def prod(ref: str, uat_image: str, expected: str, image: str = DIGEST) -> bool:
    return run("deploy-prod", {"REF": ref, "UAT_IMAGE": uat_image, "EXPECTED": expected}, image)


CASES = [
    ("uat: main", uat(MAIN, False, False, ""), True),
    ("uat: main, promote without expected_image refused", uat(MAIN, False, True, ""), False),
    ("uat: main, promote with expected_image", uat(MAIN, False, True, DIGEST), True),
    ("uat: branch refused", uat(BRANCH, False, False, ""), False),
    ("uat: branch with allow_non_main_uat", uat(BRANCH, True, False, ""), True),
    ("uat: branch + promote refused even with allow", uat(BRANCH, True, True, DIGEST), False),
    ("uat: expected_image matches (UAT only)", uat(MAIN, False, False, DIGEST), True),
    ("uat: expected_image differs", uat(MAIN, False, True, OTHER), False),
    ("prod: main, same digest, expected_image", prod(MAIN, DIGEST, DIGEST), True),
    ("prod: no expected_image refused", prod(MAIN, DIGEST, ""), False),
    ("prod: branch refused", prod(BRANCH, DIGEST, DIGEST), False),
    ("prod: UAT ran another digest", prod(MAIN, OTHER, DIGEST), False),
    ("prod: no UAT digest", prod(MAIN, "", DIGEST), False),
    ("prod: tag instead of digest", prod(MAIN, "img:tag", "img:tag", image="img:tag"), False),
    ("prod: expected_image differs", prod(MAIN, DIGEST, OTHER), False),
]

failed = [name for name, got, want in CASES if got != want]
for name, got, want in CASES:
    print(f"{'ok ' if got == want else 'BAD'} {name}: {'pass' if got else 'refuse'}")
sys.exit(1 if failed else 0)
