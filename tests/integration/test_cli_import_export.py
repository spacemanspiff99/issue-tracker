from __future__ import annotations

import json

import pytest

from issue_tracker.cli import export_json, export_recovery_bundle, import_json, restore_recovery_bundle_dry_run
from issue_tracker.services.guidance_sync import GuidanceSyncService
from issue_tracker.services.tracker import CategoryService, IssueService, ProjectService


def test_export_excludes_secrets_and_password_hashes(session, tmp_path):
    project = ProjectService(session).create_project("Tracker")
    category = CategoryService(session).create_category(project.id, "IT-1", "State", "Verify state")
    IssueService(session).create_issue(project.id, "Exported", "- [ ] exported", category_id=category.id)
    output = tmp_path / "export.json"

    export_json(session, project.id, output)

    data = json.loads(output.read_text())
    assert data["issues"][0]["acceptance_criteria"] == "- [ ] exported"
    serialized = output.read_text()
    assert "password_hash" not in serialized
    assert "APP_SECRET_KEY" not in serialized


def test_import_requires_category_mapping_when_source_categories_exist(session, tmp_path):
    payload = {
        "project": {"name": "Source"},
        "categories": [{"id": 1, "key": "SRC-1", "name": "Source category", "checklist": "Source checklist"}],
        "issues": [{"id": 1, "title": "Imported", "acceptance_criteria": "- [ ] imported", "category_id": 1}],
    }
    source = tmp_path / "source.json"
    source.write_text(json.dumps(payload))

    with pytest.raises(SystemExit, match="category mapping"):
        import_json(session, source, "Imported")

    project_id = import_json(session, source, "Imported", {"SRC-1": "IT-2"})
    assert project_id > 0


def test_recovery_bundle_exports_sanitized_manifest_and_dry_run(session, tmp_path):
    project = ProjectService(session).create_project("Tracker")
    category = CategoryService(session).create_category(project.id, "IT-1", "State", "Verify state")
    IssueService(session).create_issue(
        project.id,
        "Voice artifact",
        "- [ ] exported",
        summary="Audio artifact: `exports/voice-feedback/1/raw.webm`",
        category_id=category.id,
        labels=["backup"],
    )
    guidance = GuidanceSyncService(session)
    source = guidance.configure_source(project.id, "Tracker", "local", ["AGENTS.md"])
    guidance.classify_drift(project.id, "AGENTS.md", source_id=source.id, left_hash="a", right_hash="b")
    output_dir = tmp_path / "bundle"

    manifest = export_recovery_bundle(session, project.id, output_dir)
    dry_run = restore_recovery_bundle_dry_run(session, output_dir)
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in output_dir.rglob("*") if path.is_file())

    assert manifest.name == "manifest.json"
    assert dry_run["ok"] is True
    assert dry_run["would_create"]["issues"] == 1
    assert dry_run["would_require_category_mapping"] is True
    assert "raw.webm" not in serialized
    assert "password_hash" not in serialized
    assert "APP_SECRET_KEY" not in serialized
    assert "guidance/sources.jsonl" in manifest.read_text(encoding="utf-8")
