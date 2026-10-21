from __future__ import annotations

import json
import sys

import pytest

from issue_tracker import cli
from issue_tracker.cli import export_json, seed_demo_refusal
from issue_tracker.config import Settings
from issue_tracker.demo_data import seed_demo
from issue_tracker.domain.models import Issue, Project
from issue_tracker.mcp import tools
from issue_tracker.services.tracker import IssueService, ProjectService


def test_seed_demo_is_deterministic_and_shows_shared_sequence(session):
    result = seed_demo(session)

    assert result["created"] is True
    assert result["issues"] == {
        "0001": "Demo blocker issue",
        "0002": "Demo blocked issue",
        "0003": "Demo closed issue",
        "0005": "Demo backlog issue",
    }
    assert result["sprint"] == "0004"
    issue_id = IssueService(session).get_issue_by_sequence(result["project_id"], 3).id
    closed = tools.issue_get(session, issue_id, include_full=True)["issue"]
    assert closed["status"] == "done"
    assert closed["originating_llm"] == "demo-seed"


def test_seed_demo_rerun_is_a_noop(session):
    first = seed_demo(session)
    second = seed_demo(session)

    assert second == {"created": False, "project_id": first["project_id"], "project": "UAT Demo"}
    assert session.query(Project).count() == 1
    assert session.query(Issue).count() == 4


def test_seed_demo_leaves_other_projects_untouched(session):
    other = ProjectService(session).create_project("Existing")
    result = seed_demo(session, "Second Demo")

    assert result["project_id"] != other.id
    assert session.query(Issue).filter_by(project_id=other.id).count() == 0


def test_seed_demo_export_is_secret_free(session, tmp_path):
    project_id = seed_demo(session)["project_id"]
    output = tmp_path / "demo.json"

    export_json(session, project_id, output)

    serialized = output.read_text()
    assert json.loads(serialized)["project"]["name"] == "UAT Demo"
    for forbidden in ("password", "APP_SECRET_KEY", "session", "DATABASE_URL"):
        assert forbidden not in serialized


LOCAL_PG = "postgresql+psycopg://u:p@{host}:5432/issue_tracker"


def test_seed_demo_allows_local_and_uat_targets(tmp_path):
    no_ns = tmp_path / "missing"
    assert seed_demo_refusal("sqlite+pysqlite:///:memory:", {}, no_ns) is None
    for host in ("localhost", "127.0.0.1", "postgres"):
        assert seed_demo_refusal(LOCAL_PG.format(host=host), {}, no_ns) is None
    ns_file = tmp_path / "namespace"
    ns_file.write_text("issue-tracker-uat\n")
    in_pod = {"KUBERNETES_SERVICE_HOST": "10.43.0.1"}
    assert seed_demo_refusal(LOCAL_PG.format(host="issue-tracker-postgres"), in_pod, ns_file) is None


@pytest.mark.parametrize(
    ("environ", "namespace", "host", "reason"),
    [
        ({"KUBERNETES_SERVICE_HOST": "10.43.0.1"}, "issue-tracker", "issue-tracker-postgres", "is production"),
        ({"POD_NAMESPACE": "issue-tracker"}, None, "localhost", "is production"),
        ({"KUBERNETES_SERVICE_HOST": "10.43.0.1"}, "default", "issue-tracker-postgres", "is not 'issue-tracker-uat'"),
        ({"KUBERNETES_SERVICE_HOST": "10.43.0.1"}, None, "issue-tracker-postgres", "namespace is unknown"),
        (
            {"POD_NAMESPACE": "issue-tracker-uat"},
            None,
            "issue-tracker-postgres.issue-tracker.svc.cluster.local",
            "is not the issue-tracker-uat Postgres",
        ),
        ({}, None, "192.168.10.8", "is not local or issue-tracker-uat"),
        ({}, None, "issue-tracker-postgres.issue-tracker", "is not local or issue-tracker-uat"),
    ],
)
def test_seed_demo_refuses_production_and_non_uat_targets(tmp_path, environ, namespace, host, reason):
    ns_file = tmp_path / "namespace"
    if namespace is not None:
        ns_file.write_text(namespace)

    refusal = seed_demo_refusal(LOCAL_PG.format(host=host), environ, ns_file)

    assert refusal is not None and reason in refusal
    assert ":p@" not in refusal


def test_seed_demo_cli_refuses_before_touching_the_database(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["issue-tracker", "seed-demo"])
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(database_url=LOCAL_PG.format(host="192.168.10.8")))
    monkeypatch.setattr(cli, "SessionLocal", lambda: pytest.fail("seed-demo opened a session"))

    with pytest.raises(SystemExit, match="is not local or issue-tracker-uat"):
        cli.main()
