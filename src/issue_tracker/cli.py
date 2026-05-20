from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

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
from issue_tracker.services.tracker import CategoryService, IssueService, ProjectService


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
    args = parser.parse_args()
    with SessionLocal() as session:
        if args.command == "export-json":
            export_json(session, args.project_id, args.output)
        elif args.command == "import-json":
            project_id = import_json(session, args.input, args.project_name, parse_mapping(args.category_map))
            print(project_id)


if __name__ == "__main__":
    main()
