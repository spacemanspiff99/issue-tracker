from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session

from issue_tracker import demo_data
from issue_tracker.config import get_settings
from issue_tracker.db import SessionLocal
from issue_tracker.domain.models import (
    Category,
    Issue,
    IssueDependency,
    IssueLogEntry,
    LinkedPR,
    Sprint,
    SprintIssue,
)
from issue_tracker.markdown_import import import_markdown
from issue_tracker.services.tracker import CategoryService, DomainError, IssueService, ProjectService


def export_json(session: Session, project_id: int, output: Path) -> None:
    project = ProjectService(session).get_project(project_id)
    payload = {
        "project": {"id": project.id, "name": project.name, "repo_url": project.repo_url},
        "categories": [
            {"id": c.id, "key": c.key, "name": c.name, "checklist": c.checklist}
            for c in session.query(Category).filter_by(project_id=project_id).all()
        ],
        "issues": [
            {
                "id": i.id,
                "sequence": i.sequence,
                "title": i.title,
                "status": i.status.value,
                "acceptance_criteria": i.acceptance_criteria,
                "category_id": i.category_id,
            }
            for i in session.query(Issue).filter_by(project_id=project_id).all()
        ],
        "dependencies": [
            {"blocker_issue_id": d.blocker_issue_id, "blocked_issue_id": d.blocked_issue_id}
            for d in session.query(IssueDependency).filter_by(project_id=project_id).all()
        ],
        "sprints": [
            {"id": s.id, "sequence": s.sequence, "goal": s.goal, "status": s.status.value}
            for s in session.query(Sprint).filter_by(project_id=project_id).all()
        ],
        "sprint_issues": [
            {"sprint_id": si.sprint_id, "issue_id": si.issue_id, "status": si.status.value}
            for si in session.query(SprintIssue).join(Sprint).filter(Sprint.project_id == project_id).all()
        ],
        "issue_logs": [
            {"root_cause": entry.root_cause, "prevention_added": entry.prevention_added}
            for entry in session.query(IssueLogEntry).filter_by(project_id=project_id).all()
        ],
        "linked_prs": [
            {"repo": pr.repo, "url": pr.url, "merge_status": pr.merge_status}
            for pr in session.query(LinkedPR)
            .join(Issue, LinkedPR.issue_id == Issue.id, isouter=True)
            .filter(Issue.project_id == project_id)
            .all()
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def import_json(
    session: Session,
    input_path: Path,
    project_name: str,
    category_map: dict[str, str] | None = None,
) -> int:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    source_categories = data.get("categories", [])
    if source_categories and not category_map:
        raise SystemExit("Import with source categories requires explicit category mapping")
    project = ProjectService(session).create_project(project_name, data.get("project", {}).get("repo_url"))
    mapped_categories: dict[int, int] = {}
    for category in source_categories:
        mapped_key = category_map.get(category["key"], category["key"]) if category_map else category["key"]
        created = CategoryService(session).create_category(
            project.id, mapped_key, category["name"], category.get("checklist") or "Imported checklist"
        )
        mapped_categories[category["id"]] = created.id
    created_issues: dict[int, int] = {}
    for issue in data.get("issues", []):
        created = IssueService(session).create_issue(
            project.id,
            issue["title"],
            issue["acceptance_criteria"],
            category_id=mapped_categories.get(issue.get("category_id")),
        )
        created_issues[issue["id"]] = created.id
    for dep in data.get("dependencies", []):
        IssueService(session).add_dependency(
            created_issues[dep["blocker_issue_id"]], created_issues[dep["blocked_issue_id"]]
        )
    return project.id


def parse_mapping(values: list[str]) -> dict[str, str]:
    mapping = {}
    for value in values:
        old, sep, new = value.partition("=")
        if not sep:
            raise SystemExit("Category mappings must use OLD=NEW")
        mapping[old] = new
    return mapping


# seed-demo writes data, so it runs only against UAT (k3s `issue-tracker-uat`) or a local
# development database. Production (`issue-tracker`) and any other host are refused.
PROD_NAMESPACE = "issue-tracker"
UAT_NAMESPACE = "issue-tracker-uat"
SERVICE_ACCOUNT_NAMESPACE = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
UAT_DB_HOSTS = {
    "issue-tracker-postgres",
    f"issue-tracker-postgres.{UAT_NAMESPACE}",
    f"issue-tracker-postgres.{UAT_NAMESPACE}.svc",
    f"issue-tracker-postgres.{UAT_NAMESPACE}.svc.cluster.local",
}
# `postgres` is the Compose service name in deployment/docker-compose.local.yml.
LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


def seed_demo_refusal(
    database_url: str,
    environ: Mapping[str, str] = os.environ,
    namespace_file: Path = SERVICE_ACCOUNT_NAMESPACE,
) -> str | None:
    """Return why seed-demo must not run against this target, or None if it is UAT/local."""
    try:
        url = make_url(database_url)
    except ArgumentError:
        return "refusing seed-demo: DATABASE_URL is not a valid database URL"
    namespace = environ.get("POD_NAMESPACE", "").strip()
    if not namespace and namespace_file.is_file():
        namespace = namespace_file.read_text().strip()
    if namespace == PROD_NAMESPACE:
        return f"refusing seed-demo: namespace '{PROD_NAMESPACE}' is production"
    if namespace:
        if namespace != UAT_NAMESPACE:
            return f"refusing seed-demo: namespace '{namespace}' is not '{UAT_NAMESPACE}'"
        if url.host not in UAT_DB_HOSTS:
            return f"refusing seed-demo: database host '{url.host}' is not the {UAT_NAMESPACE} Postgres"
        return None
    if environ.get("KUBERNETES_SERVICE_HOST"):
        return "refusing seed-demo: running in a cluster but the namespace is unknown"
    if url.get_backend_name() == "sqlite" or url.host in LOCAL_DB_HOSTS:
        return None
    return f"refusing seed-demo: database host '{url.host}' is not local or {UAT_NAMESPACE}"


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export-json")
    export.add_argument("project_id", type=int)
    export.add_argument("output", type=Path)
    import_cmd = sub.add_parser("import-json")
    import_cmd.add_argument("input", type=Path)
    import_cmd.add_argument("project_name")
    import_cmd.add_argument("--category-map", action="append", default=[])
    markdown_cmd = sub.add_parser("import-markdown", help="Seed a project from documentation/issues and sprints")
    markdown_cmd.add_argument("--project", required=True)
    markdown_cmd.add_argument("--root", type=Path, default=Path("."))
    markdown_cmd.add_argument("--dry-run", action="store_true")
    demo_data.add_arguments(sub.add_parser("seed-demo"))
    args = parser.parse_args()
    if args.command == "seed-demo":
        refusal = seed_demo_refusal(get_settings().database_url)
        if refusal:
            raise SystemExit(refusal)
    with SessionLocal() as session:
        if args.command == "export-json":
            export_json(session, args.project_id, args.output)
        elif args.command == "import-json":
            project_id = import_json(session, args.input, args.project_name, parse_mapping(args.category_map))
            print(project_id)
        elif args.command == "import-markdown":
            try:
                report = import_markdown(session, args.root, args.project, dry_run=args.dry_run)
            except DomainError as exc:
                raise SystemExit(f"import-markdown: {exc}") from exc
            for action in report.actions:
                print(action)
            prefix = "dry-run: would have " if args.dry_run else ""
            print(f"{prefix}{report.created} created / {report.updated} updated / {report.unchanged} unchanged")
        elif args.command == "seed-demo":
            demo_data.run(session, args)


if __name__ == "__main__":
    main()
