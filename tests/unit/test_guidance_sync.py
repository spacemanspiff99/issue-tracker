from issue_tracker.services.guidance_sync import GuidanceSyncService
from issue_tracker.services.tracker import IssueService, ProjectService


def test_guidance_source_scan_excludes_artifacts_and_records_snapshots(session, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("rules\n", encoding="utf-8")
    (repo / ".env").write_text("SECRET=bad\n", encoding="utf-8")
    (repo / "exports").mkdir()
    (repo / "exports" / "dump.txt").write_text("ignore\n", encoding="utf-8")

    project = ProjectService(session).create_project("Tracker")
    service = GuidanceSyncService(session)
    service._git = lambda _repo_path, args: "main\n" if args[:1] == ["branch"] else "abc123\n"
    source = service.configure_source(
        project.id,
        "issue-tracker",
        str(repo),
        ["AGENTS.md", ".env", "exports"],
        default_branch="main",
        vibecoding_target_path="projects/issue-tracker",
    )
    snapshots = service.scan_source(source.id, repo)

    assert service.list_branches(repo) == ["main"]
    assert [snapshot.path for snapshot in snapshots] == ["AGENTS.md"]
    assert snapshots[0].commit_sha
    assert source.scan_status == "ok"


def test_guidance_scan_missing_repo_is_auth_blocked(session, tmp_path):
    project = ProjectService(session).create_project("Tracker")
    service = GuidanceSyncService(session)
    source = service.configure_source(project.id, "private", "git@example.com:private/repo.git", ["AGENTS.md"])

    snapshots = service.scan_source(source.id, tmp_path / "missing")

    assert snapshots == []
    assert source.scan_status == "auth-blocked"


def test_guidance_drift_classification(session):
    project = ProjectService(session).create_project("Tracker")
    service = GuidanceSyncService(session)

    in_sync = service.classify_drift(project.id, "AGENTS.md", left_hash="a", right_hash="a")
    local_only = service.classify_drift(project.id, "AGENTS.md", left_hash="a", right_hash=None, right_exists=False)
    protected = service.classify_drift(
        project.id,
        "documentation/design/magicpatterns/UI.tsx",
        left_hash="a",
        right_hash="b",
        protected=True,
    )
    auth_blocked = service.classify_drift(project.id, "AGENTS.md", scan_status="auth-blocked")

    assert in_sync.drift_type == "in-sync"
    assert in_sync.recommended_action == "skip"
    assert local_only.drift_type == "local-only"
    assert local_only.recommended_action == "copy"
    assert protected.drift_type == "protected-change"
    assert protected.severity == "high"
    assert auth_blocked.drift_type == "auth-blocked"
    assert auth_blocked.recommended_action == "investigate"


def test_guidance_snapshot_set_comparison_detects_renames_and_target_only(session):
    project = ProjectService(session).create_project("Tracker")
    service = GuidanceSyncService(session)

    drifts = service.compare_snapshot_sets(
        project.id,
        left={"AGENTS.md": "same", "old.md": "moved"},
        right={"AGENTS.md": "same", "new.md": "moved", "mirror-only.md": "remote"},
    )

    by_type = {drift.drift_type: drift for drift in drifts}
    assert by_type["renamed"].path == "old.md -> new.md"
    assert by_type["target-only"].path == "mirror-only.md"
    assert by_type["in-sync"].path == "AGENTS.md"


def test_guidance_proposal_execution_ingestion_and_rollback(session):
    project = ProjectService(session).create_project("Tracker")
    issue = IssueService(session).create_issue(project.id, "Repair guidance", "- [ ] verified")
    service = GuidanceSyncService(session)
    drift = service.classify_drift(project.id, "AGENTS.md", left_hash="a", right_hash="b")

    proposal = service.create_proposal(
        project.id,
        drift.id,
        "merge-needed",
        issue.id,
        owner="codex",
        verification_command="python -m pytest tests/unit/test_guidance_sync.py",
    )
    duplicate = service.create_proposal(
        project.id,
        drift.id,
        "merge-needed",
        issue.id,
        owner="codex",
        verification_command="python -m pytest tests/unit/test_guidance_sync.py",
    )
    ready = service.move_proposal_ready(proposal.id)
    run = service.execute_proposal(ready.id, actor="codex")
    event = service.ingest_event(project.id, "owner/repo", "main", "abcdef123", ["AGENTS.md"])
    duplicate_event = service.ingest_event(project.id, "owner/repo", "main", "abcdef123", ["AGENTS.md"])

    assert duplicate.id == proposal.id
    assert ready.status == "ready"
    assert run.status == "dry-run"
    assert "Linked tracker issue" in run.logs
    assert event.id == duplicate_event.id
    assert "Rollback plan" in service.rollback_plan(run.id)


def test_guidance_protected_proposal_requires_explicit_approval(session):
    project = ProjectService(session).create_project("Tracker")
    issue = IssueService(session).create_issue(project.id, "Protected repair", "- [ ] verified")
    service = GuidanceSyncService(session)
    drift = service.classify_drift(
        project.id,
        "documentation/design/magicpatterns/UI.tsx",
        left_hash="a",
        right_hash="b",
        protected=True,
    )
    proposal = service.create_proposal(
        project.id,
        drift.id,
        "investigate",
        issue.id,
        owner="codex",
        verification_command="python -m pytest",
    )

    try:
        service.move_proposal_ready(proposal.id)
    except Exception as exc:
        assert "Protected guidance" in str(exc)
    else:
        raise AssertionError("protected proposal moved without approval")

    approved = service.move_proposal_ready(proposal.id, approval_text="approve protected guidance investigation")
    assert approved.status == "ready"
