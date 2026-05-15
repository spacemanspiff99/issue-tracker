from __future__ import annotations

import json

import pytest

from issue_tracker.cli import export_json, import_json
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
