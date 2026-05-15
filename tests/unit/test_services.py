from __future__ import annotations

import pytest

from issue_tracker.domain.enums import IssueStatus
from issue_tracker.services.tracker import CategoryService, DomainError, IssueService, ProjectService, SprintService


def test_shared_project_sequence_for_issues_and_sprints(session):
    project = ProjectService(session).create_project("Tracker")
    issue = IssueService(session).create_issue(project.id, "First issue", "- [ ] prove it")
    sprint = SprintService(session).create_sprint(project.id, "MVP")

    assert issue.sequence == 1
    assert sprint.sequence == 2
    assert issue.slug.startswith("0001-")
    assert sprint.slug.startswith("0002-")


def test_acceptance_criteria_are_required(session):
    project = ProjectService(session).create_project("Tracker")

    with pytest.raises(DomainError, match="Acceptance criteria"):
        IssueService(session).create_issue(project.id, "No AC", "")


def test_dependency_cycle_is_rejected(session):
    project = ProjectService(session).create_project("Tracker")
    service = IssueService(session)
    first = service.create_issue(project.id, "First", "- [ ] first")
    second = service.create_issue(project.id, "Second", "- [ ] second")

    service.add_dependency(first.id, second.id)

    with pytest.raises(DomainError, match="cycle"):
        service.add_dependency(second.id, first.id)


def test_close_metadata_is_required_and_immutable(session):
    project = ProjectService(session).create_project("Tracker")
    service = IssueService(session)
    issue = service.create_issue(project.id, "Close me", "- [ ] closed")

    with pytest.raises(DomainError, match="Originating LLM"):
        service.update_status(issue.id, "done")

    closed = service.update_status(issue.id, "done", originating_llm="gpt-5.5", closed_by="tester")
    assert closed.status == IssueStatus.DONE
    assert closed.closed_at is not None

    with pytest.raises(DomainError, match="immutable"):
        service.update_status(issue.id, "backlog")


def test_categories_are_project_scoped_not_peer_taxonomy_constants(session):
    first = ProjectService(session).create_project("Tracker")
    second = ProjectService(session).create_project("Other")
    categories = CategoryService(session)
    first_category = categories.create_category(first.id, "IT-1", "Tracker State", "Verify tracker state")
    categories.create_category(second.id, "CAT-1", "Peer Example", "Project-owned checklist")

    issue = IssueService(session).create_issue(
        first.id,
        "Bound to local category",
        "- [ ] category checklist is local",
        category_id=first_category.id,
    )

    assert issue.category_id == first_category.id
    with pytest.raises(DomainError, match="another project"):
        IssueService(session).create_issue(
            second.id,
            "Wrong category",
            "- [ ] no leakage",
            category_id=first_category.id,
        )
