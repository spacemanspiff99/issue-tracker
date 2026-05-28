from __future__ import annotations

import pytest

from issue_tracker.domain.enums import IssueStatus, SprintStatus
from issue_tracker.services.tracker import (
    CategoryService,
    DomainError,
    IssueLogService,
    IssueService,
    ProjectService,
    SprintService,
)


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


def test_cancelled_status_has_terminal_metadata_and_separate_saved_view(session):
    project = ProjectService(session).create_project("Tracker")
    service = IssueService(session)
    cancelled = service.create_issue(project.id, "Won't do", "- [ ] cancelled")
    service.create_issue(project.id, "Open", "- [ ] open")

    closed = service.update_status(
        cancelled.id,
        "cancelled",
        originating_llm="gpt-5.5",
        closed_by="tester",
        close_note="not worth doing",
    )

    assert closed.status == IssueStatus.CANCELLED
    assert closed.closed_at is not None
    assert [issue.title for issue in service.list_project_view(project.id, "cancelled")] == ["Won't do"]
    assert [issue.title for issue in service.list_project_view(project.id, "not-in-sprint")] == ["Open"]
    assert service.project_summary(project.id)["done_percent"] == 0
    with pytest.raises(DomainError, match="immutable"):
        service.update_status(cancelled.id, "backlog")


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
    with pytest.raises(DomainError, match="Category was not found"):
        IssueService(session).create_issue(
            first.id,
            "Missing category",
            "- [ ] reject missing category",
            category_id=999,
        )
    with pytest.raises(DomainError, match="another project"):
        IssueService(session).create_issue(
            second.id,
            "Wrong category",
            "- [ ] no leakage",
            category_id=first_category.id,
        )


def test_closed_sprints_reject_new_issue_assignment(session):
    project = ProjectService(session).create_project("Tracker")
    issue = IssueService(session).create_issue(project.id, "Late add", "- [ ] rejected")
    service = SprintService(session)
    sprint = service.create_sprint(project.id, "Closed sprint")

    service.close_sprint(sprint.id)

    assert sprint.status == SprintStatus.CLOSED
    with pytest.raises(DomainError, match="Closed sprints"):
        service.add_issue(sprint.id, issue.id)


def test_saved_views_rollups_metadata_comments_and_references(session):
    project = ProjectService(session).create_project("Tracker")
    categories = CategoryService(session)
    taxonomy = categories.ensure_base_taxonomy(project.id)
    service = IssueService(session)
    blocker = service.create_issue(project.id, "Blocker", "- [ ] blocker", category_id=taxonomy[0].id)
    blocked = service.create_issue(project.id, "Blocked", "- [ ] blocked")
    done = service.create_issue(project.id, "Done", "- [ ] done")
    not_in_sprint = service.create_issue(project.id, "Not sprinted", "- [ ] plan me")

    service.add_dependency(blocker.id, blocked.id)
    sprint = SprintService(session).create_sprint(project.id, "MVP")
    SprintService(session).add_issue(sprint.id, blocked.id)
    service.update_status(done.id, "done", originating_llm="gpt-5.5", closed_by="tester")
    service.update_planning_metadata(
        blocked.id,
        labels="ui, urgent",
        story="Modern UI",
        delivery_phase="Build",
        milestone="MVP",
        custom_fields="risk=medium",
        actor="tester",
    )
    service.add_comment(blocked.id, "Needs browser pass", actor="tester")
    linked = service.add_linked_reference(blocked.id, "owner/repo", "https://github.com/owner/repo/pull/1")

    assert [issue.title for issue in service.list_project_view(project.id, "blocked")] == ["Blocked"]
    assert [issue.title for issue in service.list_project_view(project.id, "active-sprint")] == ["Blocked"]
    assert [issue.title for issue in service.list_project_view(project.id, "done")] == ["Done"]
    assert [issue.title for issue in service.list_project_view(project.id, "not-in-sprint")] == [
        "Blocker",
        "Not sprinted",
    ]
    assert service.project_summary(project.id)["blocked"] == 1
    dashboard = service.overview_dashboard(project.id)
    assert dashboard["delivery_phases"]["Build"] == 1
    assert dashboard["blocked_items"][0]["issue"].title == "Blocked"
    assert dashboard["blocked_items"][0]["reason"] == "0001 Blocker"
    assert dashboard["active_sprint_total"] == 1
    assert service.sprint_rollups(project.id)[0]["stories"] == {"Modern UI": 1}
    assert service.get_issue(blocked.id).labels["custom_fields"] == {"risk": "medium"}
    assert service.activity_feed(project.id)[0].message
    assert linked.repo == "owner/repo"
    assert not_in_sprint.status == IssueStatus.BACKLOG


def test_issue_log_agent_failure_and_bug_patterns(session):
    project = ProjectService(session).create_project("Tracker")
    category = CategoryService(session).create_category(project.id, "IT-1", "Tracker State", "Keep tracker aligned")
    issue = IssueService(session).create_issue(project.id, "Autonomous sprint", "- [ ] complete")
    logs = IssueLogService(session)

    failure = logs.create_agent_failure(
        project.id,
        target="iterate until sprint complete",
        observed_failure="stopped after a slice",
        prevention_added="Require full-sprint STOP evidence before handoff.",
        issue_id=issue.id,
        category_id=category.id,
        severity="high",
        source_context="Sprint 0084",
    )
    bug = logs.create_bug_record(
        project.id,
        bug="voice intake not saved",
        root_cause="recording was attached but not persisted",
        prevention_added="Autosave recording on stop.",
        issue_id=issue.id,
        category_id=category.id,
        severity="urgent",
    )

    assert failure.issue_id == issue.id
    assert "agent-failure" in failure.root_cause
    assert "severity=high" in failure.root_cause
    assert "source=Sprint 0084" in failure.root_cause
    assert bug.category_id == category.id
    assert logs.pattern_summary(project.id) == {"bug": 1, "agent-failure": 1}


def test_backlog_reorder_and_category_recommendation(session):
    project = ProjectService(session).create_project("Tracker")
    category = CategoryService(session).create_category(project.id, "UI", "User Interface", "Review forms")
    service = IssueService(session)
    first = service.create_issue(project.id, "First", "- [ ] first")
    second = service.create_issue(project.id, "Second", "- [ ] second")

    service.reorder_backlog(project.id, [second.id, first.id])

    assert [issue.id for issue in service.list_project_view(project.id, "backlog")] == [second.id, first.id]
    assert service.category_recommendation(project.id, "Improve interface forms").id == category.id


def test_release_workflow_and_voice_intake_metadata(session, tmp_path):
    project = ProjectService(session).create_project("Tracker")
    service = IssueService(session)
    first = service.create_issue(project.id, "MVP issue", "- [ ] ships")
    second = service.create_issue(project.id, "v1 issue", "- [ ] follows")
    sprint = SprintService(session).create_sprint(project.id, "MVP sprint")

    SprintService(session).add_issue(sprint.id, first.id)
    service.update_planning_metadata(
        first.id,
        milestone="MVP release",
        custom_fields="readiness=route tests passing",
    )
    service.update_planning_metadata(second.id, milestone="v1.0")
    service.add_dependency(first.id, second.id)
    service.update_workflow_state(second.id, "clarify", actor="tester")
    intake = service.create_voice_intake(
        project.id,
        "ambiguous audio",
        "Need more context",
        tmp_path / "audio.webm",
        ambiguous=True,
        actor="tester",
    )

    releases = {release["name"]: release for release in service.release_rollups(project.id)}
    assert releases["MVP release"]["done_percent"] == 0
    assert releases["MVP release"]["unscheduled"] == 0
    assert releases["MVP release"]["readiness_notes"] == ["route tests passing"]
    assert releases["v1.0"]["blocked"] == 1
    assert releases["v1.0"]["unscheduled"] == 1
    assert releases["v1.0"]["section"] == "current"
    assert service.release_sections(project.id)["current"][0]["name"] == "v1.0"
    assert service.workflow_state(second) == "needs-clarification"
    assert service.workflow_state(intake) == "needs-clarification"
    assert intake.labels["custom_fields"]["intake_type"] == "voice-feedback"


def test_audio_only_urgent_voice_intake_gets_processable_title_and_priority(session, tmp_path):
    project = ProjectService(session).create_project("Tracker")
    intake = IssueService(session).create_voice_intake(
        project.id,
        "",
        "",
        tmp_path / "urgent.webm",
        ambiguous=False,
        priority="urgent",
        actor="tester",
    )

    assert intake.title == "Voice feedback: To process: urgent audio note"
    assert intake.priority == "urgent"
    assert "Audio-only urgent voice note" in intake.summary
    assert "urgent" in intake.labels["items"]
    assert intake.labels["custom_fields"]["workflow_state"] == "needs-processing"


def test_audio_only_voice_intake_gets_processable_title_without_priority(session, tmp_path):
    project = ProjectService(session).create_project("Tracker")
    intake = IssueService(session).create_voice_intake(
        project.id,
        "",
        "",
        tmp_path / "audio.webm",
        ambiguous=False,
        priority="",
        actor="tester",
    )

    assert intake.title == "Voice feedback: To process: audio note"
    assert intake.priority == "normal"
    assert intake.labels["custom_fields"]["workflow_state"] == "needs-processing"


def test_voice_intake_discard_rejects_durable_work(session, tmp_path):
    project = ProjectService(session).create_project("Tracker")
    service = IssueService(session)
    intake = service.create_voice_intake(
        project.id,
        "",
        "",
        tmp_path / "audio.webm",
        ambiguous=False,
        actor="tester",
    )
    sprint = SprintService(session).create_sprint(project.id, "Process intake")
    SprintService(session).add_issue(sprint.id, intake.id)

    with pytest.raises(DomainError, match="Durable work"):
        service.delete_voice_intake(intake.id, actor="tester")
