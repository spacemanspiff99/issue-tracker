from __future__ import annotations

from pathlib import Path

import pytest

from issue_tracker.domain.enums import IssueStatus, SprintStatus
from issue_tracker.domain.models import Category, Issue, IssueEvent, Project, Sprint, SprintIssue
from issue_tracker.markdown_import import import_markdown, parse_markdown_file
from issue_tracker.services.tracker import (
    CategoryService,
    DomainError,
    IssueService,
    ProjectService,
    SprintService,
)

SPRINT = """# Sprint 0003: Seed Sprint

Status: planned

## Goal

Ship the seed.
"""

ISSUE_TEMPLATE = """# Issue {seq}: {title}

Status: {status}
Category gates: {gates}
Sprint: Sprint 0003

## Problem

Something is missing.

## Acceptance Criteria

- [x] parsed
- [ ] imported

## Category Checklists

`QA-1` Quality Gate: Verify the thing.

## STOP

Stop.
"""


def write_tree(root: Path, issues: dict[str, tuple[str, str, str]]) -> None:
    (root / "documentation" / "issues").mkdir(parents=True, exist_ok=True)
    (root / "documentation" / "sprints").mkdir(parents=True, exist_ok=True)
    (root / "documentation" / "sprints" / "0003-seed-sprint.md").write_text(SPRINT)
    for seq, (title, status, gates) in issues.items():
        body = ISSUE_TEMPLATE.format(seq=seq, title=title, status=status, gates=gates)
        (root / "documentation" / "issues" / f"{seq}-x.md").write_text(body)


@pytest.fixture()
def tree(tmp_path):
    write_tree(
        tmp_path,
        {
            "0004": ("First Seed", "backlog", "`QA-1`, `QA-2`"),
            "0007": ("Second Seed", "in-progress", "`QA-2`"),
            "0009": ("Third Seed", "done", "`QA-1`"),
        },
    )
    return tmp_path


def counts(session) -> dict[str, int]:
    models = (Project, Category, Issue, Sprint, SprintIssue, IssueEvent)
    return {m.__tablename__: session.query(m).count() for m in models}


def test_parse_issue_file(tree):
    item = parse_markdown_file(tree / "documentation" / "issues" / "0004-x.md")

    assert (item.kind, item.sequence, item.title, item.status) == ("issue", 4, "First Seed", "backlog")
    assert item.acceptance_criteria == "- [x] parsed\n- [ ] imported"
    assert item.category_keys == ["QA-1", "QA-2"]
    assert item.category_defs == {"QA-1": ("Quality Gate", "Verify the thing.")}
    assert item.sprint_sequence == 3
    assert item.summary == "Something is missing."


def test_parse_sprint_file(tree):
    item = parse_markdown_file(tree / "documentation" / "sprints" / "0003-seed-sprint.md")

    assert (item.kind, item.sequence, item.title, item.status) == ("sprint", 3, "Seed Sprint", "planned")


def test_parse_rejects_unknown_status(tmp_path):
    path = tmp_path / "0001-bad.md"
    path.write_text("# Issue 0001: Bad\n\nStatus: someday\n")

    with pytest.raises(DomainError, match="unknown issue status"):
        parse_markdown_file(path)


def test_parse_normalizes_free_text_status(tmp_path):
    path = tmp_path / "0001-review.md"
    path.write_text("# Issue 0001: Review\n\nStatus: in review (PR open, not merged)\n")

    assert parse_markdown_file(path).status == "in-progress"


def test_dry_run_writes_nothing(session, tree):
    before = counts(session)

    report = import_markdown(session, tree, "Seeded", dry_run=True)

    assert counts(session) == before
    assert report.created == 1 + 2 + 1 + 3  # project, categories, sprint, issues
    assert any("issue 0009 Third Seed" in action for action in report.actions)
    assert any("sprint 0003 Seed Sprint" in action for action in report.actions)


def test_import_preserves_sequence_title_status_ac_and_sprint(session, tree):
    import_markdown(session, tree, "Seeded")

    project = ProjectService(session).get_project_by_name("Seeded")
    issues = {i.sequence: i for i in session.query(Issue).filter_by(project_id=project.id)}
    assert sorted(issues) == [4, 7, 9]
    assert issues[4].title == "First Seed"
    assert issues[4].status == IssueStatus.BACKLOG
    assert issues[7].status == IssueStatus.IN_PROGRESS
    assert issues[9].status == IssueStatus.DONE
    assert issues[9].closed_at is not None and issues[9].originating_llm == "markdown-import"
    assert issues[4].acceptance_criteria == "- [x] parsed\n- [ ] imported"
    sprint = SprintService(session).get_sprint_by_sequence(project.id, 3)
    assert sprint.status == SprintStatus.PLANNED
    assert {m.issue_id for m in SprintService(session).list_issues(sprint.id)} == {i.id for i in issues.values()}
    assert issues[4].labels == {"items": ["QA-1", "QA-2"]}


def test_categories_come_from_files_and_are_project_scoped(session, tree):
    other = ProjectService(session).create_project("Other")
    CategoryService(session).create_category(other.id, "QA-1", "Other gate", "Other checklist")

    import_markdown(session, tree, "Seeded")

    project = ProjectService(session).get_project_by_name("Seeded")
    categories = {c.key: c for c in CategoryService(session).list_categories(project.id)}
    assert set(categories) == {"QA-1", "QA-2"}
    assert categories["QA-1"].name == "Quality Gate"
    assert categories["QA-1"].checklist == "Verify the thing."
    issue = IssueService(session).get_issue_by_sequence(project.id, 4)
    assert issue.category_id == categories["QA-1"].id


def test_next_allocated_id_is_above_highest_imported(session, tree):
    import_markdown(session, tree, "Seeded")
    project = ProjectService(session).get_project_by_name("Seeded")

    created = IssueService(session).create_issue(project.id, "After import", "- [ ] next")

    assert created.sequence == 10


def test_second_run_reports_no_changes(session, tree):
    import_markdown(session, tree, "Seeded")
    before = counts(session)

    report = import_markdown(session, tree, "Seeded")

    assert (report.created, report.updated) == (0, 0)
    assert counts(session) == before


def test_rerun_applies_ac_and_status_changes(session, tree):
    import_markdown(session, tree, "Seeded")
    path = tree / "documentation" / "issues" / "0004-x.md"
    path.write_text(path.read_text().replace("- [ ] imported", "- [x] imported").replace("backlog", "done"))

    report = import_markdown(session, tree, "Seeded")

    assert (report.created, report.updated) == (0, 1)
    project = ProjectService(session).get_project_by_name("Seeded")
    issue = IssueService(session).get_issue_by_sequence(project.id, 4)
    assert issue.acceptance_criteria.endswith("- [x] imported")
    assert issue.status == IssueStatus.DONE and issue.closed_at is not None
    assert (import_markdown(session, tree, "Seeded").updated, report.created) == (0, 0)


def test_explicit_sequence_collision_is_rejected(session):
    project = ProjectService(session).create_project("Tracker")
    SprintService(session).create_sprint(project.id, "Sprint", sequence=5)

    with pytest.raises(DomainError, match="0005"):
        IssueService(session).create_issue(project.id, "Clash", "- [ ] clash", sequence=5)
