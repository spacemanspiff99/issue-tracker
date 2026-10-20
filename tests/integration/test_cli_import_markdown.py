from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from issue_tracker.markdown_import import parse_markdown_file, parse_tree
from issue_tracker.services.tracker import DomainError

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_FILES = sorted(REPO_ROOT.glob("documentation/issues/*.md")) + sorted(REPO_ROOT.glob("documentation/sprints/*.md"))


@pytest.mark.parametrize("path", REPO_FILES, ids=lambda p: p.name)
def test_every_repo_markdown_file_parses(path):
    item = parse_markdown_file(path)

    assert path.name.startswith(f"{item.sequence:04d}-")
    if item.kind == "issue":
        assert item.acceptance_criteria


def test_parse_tree_rejects_shared_sequence_collision(tmp_path):
    for folder in ("issues", "sprints"):
        (tmp_path / "documentation" / folder).mkdir(parents=True)
    (tmp_path / "documentation/issues/0002-a.md").write_text("# Issue 0002: A\n\n## Acceptance Criteria\n\n- [ ] a\n")
    (tmp_path / "documentation/sprints/0002-b.md").write_text("# Sprint 0002: B\n")

    with pytest.raises(DomainError, match="Sequence 0002 used by"):
        parse_tree(tmp_path)


def run_cli(tmp_path, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {"DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'cli.db'}"}
    args = ["import-markdown", "--project", "issue-tracker", "--root", str(root), *extra]
    return subprocess.run(
        [sys.executable, "-m", "issue_tracker.cli", *args], env=env, capture_output=True, text=True
    )


def write_doc(root: Path, folder: str, name: str, body: str) -> None:
    path = root / "documentation" / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


def test_cli_dry_run_import_and_rerun(tmp_path):
    root = tmp_path / "repo"
    write_doc(root, "sprints", "0001-seed.md", "# Sprint 0001: Seed Sprint\n\nStatus: planned\n")
    issue = "# Issue {n}: Seed {n}\n\nStatus: {s}\nCategory gates: `QA-1`\nSprint: Sprint 0001\n\n"
    issue += "## Acceptance Criteria\n\n- [ ] works\n"
    write_doc(root, "issues", "0002-a.md", issue.format(n="0002", s="backlog"))
    write_doc(root, "issues", "0003-b.md", issue.format(n="0003", s="in review (PR open)"))
    bootstrap = "from issue_tracker.db import engine; from issue_tracker.domain.models import Base;"
    bootstrap += "Base.metadata.create_all(engine)"
    env = {"DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'cli.db'}"}
    subprocess.run([sys.executable, "-c", bootstrap], env=env, check=True)

    dry = run_cli(tmp_path, root, "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert "create: issue 0003 Seed 0003 [in-progress]" in dry.stdout
    assert "create: sprint 0001 Seed Sprint" in dry.stdout
    assert dry.stdout.strip().splitlines()[-1] == "dry-run: would have 5 created / 0 updated / 0 unchanged"

    first = run_cli(tmp_path, root)
    assert first.returncode == 0, first.stderr
    assert first.stdout.strip().splitlines()[-1] == "5 created / 0 updated / 0 unchanged"

    second = run_cli(tmp_path, root)
    assert second.returncode == 0, second.stderr
    assert second.stdout.strip().splitlines()[-1] == "0 created / 0 updated / 4 unchanged"


def test_cli_reports_collision_without_traceback(tmp_path):
    for folder in ("issues", "sprints"):
        (tmp_path / "documentation" / folder).mkdir(parents=True)
    (tmp_path / "documentation/issues/0002-a.md").write_text("# Issue 0002: A\n\n## Acceptance Criteria\n\n- [ ] a\n")
    (tmp_path / "documentation/sprints/0002-b.md").write_text("# Sprint 0002: B\n")

    result = run_cli(tmp_path, tmp_path, "--dry-run")

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "import-markdown: Sequence 0002 used by" in result.stderr
