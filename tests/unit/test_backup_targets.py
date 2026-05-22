from __future__ import annotations

from issue_tracker.services.backup_targets import ArtifactBackupAdapter, VibecodingBackupService
from issue_tracker.services.recovery_bundle import RecoveryBundleService
from issue_tracker.services.tracker import IssueService, ProjectService


def test_vibecoding_backup_plan_and_missing_token_block_publication(session, tmp_path, monkeypatch):
    project = ProjectService(session).create_project("Issue Tracker", repo_url="git@example.com:issue-tracker.git")
    IssueService(session).create_issue(project.id, "Backed up", "- [ ] recoverable")
    bundle_dir = tmp_path / "bundle"
    RecoveryBundleService(session).export_bundle(project.id, bundle_dir)
    monkeypatch.delenv("VIBECODING_MIRROR_TOKEN", raising=False)

    service = VibecodingBackupService(session)
    paths = service.plan_target_paths(project.id)
    result = service.publish_bundle(project.id, bundle_dir)

    assert paths["latest"] == "projects/issue-tracker/tracker-backups/latest"
    assert "snapshots" in paths["snapshot"]
    assert result.status == "blocked"
    assert result.blocked_reason == "VIBECODING_MIRROR_TOKEN is not available"
    assert result.provenance["tracker_project_id"] == project.id


def test_vibecoding_backup_publication_writes_only_sanitized_bundle(session, tmp_path, monkeypatch):
    project = ProjectService(session).create_project("Issue Tracker")
    IssueService(session).create_issue(project.id, "Backed up", "- [ ] recoverable")
    bundle_dir = tmp_path / "bundle"
    target_root = tmp_path / "vibecoding"
    RecoveryBundleService(session).export_bundle(project.id, bundle_dir)
    monkeypatch.setenv("VIBECODING_MIRROR_TOKEN", "test-token")

    result = VibecodingBackupService(session).publish_bundle(
        project.id,
        bundle_dir,
        vibecoding_root=target_root,
        dry_run=False,
    )

    latest = target_root / result.target_path
    snapshot = target_root / result.snapshot_path
    assert result.status == "published"
    assert (latest / "manifest.json").exists()
    assert (latest / "publication-provenance.json").exists()
    assert (snapshot / "manifest.json").exists()
    assert not list(latest.rglob("*.webm"))


def test_artifact_backup_missing_tool_or_credentials_is_owner_action_blocker(tmp_path, monkeypatch):
    artifact = tmp_path / "raw.webm"
    artifact.write_bytes(b"audio")
    monkeypatch.setattr("shutil.which", lambda _name: None)

    result = ArtifactBackupAdapter().prepare_backup([artifact], backend="restic")

    assert result.status == "blocked"
    assert "Owner action required" in result.next_action
    assert result.manifest["artifacts"][0]["kind"] == "raw-audio"
    assert result.archive_id is None
