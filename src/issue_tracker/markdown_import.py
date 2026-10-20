"""Seed a project from repo-local markdown issues and sprints (`issue-tracker import-markdown`).

Every write goes through the service layer; this module only parses files and diffs them
against what the project already holds, so a re-run is a no-op when nothing changed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from issue_tracker.domain.enums import IssueStatus, SprintStatus
from issue_tracker.services.tracker import (
    CategoryService,
    DomainError,
    IssueService,
    ProjectService,
    SprintService,
    display_id,
)

HEADER_RE = re.compile(r"^#\s+(Issue|Sprint)\s+(\d+):\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z ]*):\s*(.*?)\s*$")
CHECKLIST_RE = re.compile(r"^`([^`]+)`\s+([^:]+):\s*(.+?)\s*$")
SPRINT_REF_RE = re.compile(r"Sprint\s+(\d+)")
IMPORT_LLM = "markdown-import"
# Markdown status lines are free text ("in review (PR open, not merged)"); map known prefixes.
ISSUE_STATUS_ALIASES = {"in review": "in-progress", "in progress": "in-progress", "closed": "done"}
SPRINT_STATUS_ALIASES = {"done": "closed", "in-progress": "active", "in progress": "active"}


@dataclass
class MarkdownItem:
    kind: str
    sequence: int
    title: str
    status: str
    path: Path
    acceptance_criteria: str = ""
    summary: str | None = None
    category_keys: list[str] = field(default_factory=list)
    category_defs: dict[str, tuple[str, str]] = field(default_factory=dict)
    sprint_sequence: int | None = None
    originating_llm: str | None = None


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    actions: list[str] = field(default_factory=list)

    def note(self, kind: str, message: str) -> None:
        if kind == "create":
            self.created += 1
        elif kind == "update":
            self.updated += 1
        else:
            self.unchanged += 1
        self.actions.append(f"{kind}: {message}")


def _sections(lines: list[str]) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lines:
        if line.startswith("## "):
            current = sections.setdefault(line[3:].strip().lower(), [])
        elif current is not None:
            current.append(line)
    return {name: "\n".join(body).strip() for name, body in sections.items()}


def parse_markdown_file(path: Path) -> MarkdownItem:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = HEADER_RE.match(lines[0]) if lines else None
    if header is None:
        raise DomainError(f"{path}: first line must be '# Issue NNNN: Title' or '# Sprint NNNN: Title'")
    kind, number, title = header.group(1).lower(), int(header.group(2)), header.group(3)
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.startswith("## "):
            break
        match = FIELD_RE.match(line)
        if match:
            fields.setdefault(match.group(1).strip().lower(), match.group(2))
    sections = _sections(lines)
    default_status = IssueStatus.BACKLOG.value if kind == "issue" else SprintStatus.PLANNED.value
    item = MarkdownItem(
        kind=kind,
        sequence=number,
        title=title,
        status=_normalize_status(path, kind, fields.get("status", default_status)),
        path=path,
        originating_llm=fields.get("originating model") or fields.get("originating llm") or None,
    )
    if kind == "sprint":
        item.summary = sections.get("goal") or None
        return item
    item.acceptance_criteria = "\n".join(
        line.strip() for line in sections.get("acceptance criteria", "").splitlines() if line.strip()
    )
    item.summary = sections.get("problem") or sections.get("context") or None
    item.category_keys = re.findall(r"`([^`]+)`", fields.get("category gates", ""))
    for line in sections.get("category checklists", "").splitlines():
        match = CHECKLIST_RE.match(line.strip())
        if match:
            item.category_defs[match.group(1)] = (match.group(2).strip(), match.group(3))
    sprint_ref = SPRINT_REF_RE.search(fields.get("sprint", ""))
    item.sprint_sequence = int(sprint_ref.group(1)) if sprint_ref else None
    return item


def _normalize_status(path: Path, kind: str, raw: str) -> str:
    text = raw.strip().lower()
    enum = IssueStatus if kind == "issue" else SprintStatus
    aliases = ISSUE_STATUS_ALIASES if kind == "issue" else SPRINT_STATUS_ALIASES
    for prefix, status in [*((s.value, s.value) for s in enum), *aliases.items()]:
        if text == prefix or text.startswith(prefix + " "):
            return status
    raise DomainError(f"{path}: unknown {kind} status {raw!r}")


def parse_tree(root: Path) -> list[MarkdownItem]:
    paths = sorted((root / "documentation" / "issues").glob("*.md"))
    paths += sorted((root / "documentation" / "sprints").glob("*.md"))
    items = [parse_markdown_file(path) for path in paths]
    seen: dict[int, Path] = {}
    for item in items:
        if item.sequence in seen:
            raise DomainError(f"Sequence {display_id(item.sequence)} used by {seen[item.sequence]} and {item.path}")
        seen[item.sequence] = item.path
    return sorted(items, key=lambda item: item.sequence)


def import_markdown(session: Session, root: Path, project_name: str, dry_run: bool = False) -> ImportReport:
    items = parse_tree(root)
    report = ImportReport()
    project = ProjectService(session).get_project_by_name(project_name)
    if project is None:
        report.note("create", f"project {project_name}")
        if not dry_run:
            project = ProjectService(session).create_project(project_name)
    project_id = project.id if project else None

    categories = _sync_categories(session, project_id, items, report, dry_run)
    sprints: dict[int, int | None] = {}
    for item in (i for i in items if i.kind == "sprint"):
        sprints[item.sequence] = _sync_sprint(session, project_id, item, report, dry_run)
    for item in (i for i in items if i.kind == "issue"):
        if item.sprint_sequence is not None and item.sprint_sequence not in sprints:
            raise DomainError(f"{item.path}: Sprint {display_id(item.sprint_sequence)} has no markdown file")
        _sync_issue(session, project_id, item, categories, sprints, report, dry_run)
    return report


def _sync_categories(
    session: Session, project_id: int | None, items: list[MarkdownItem], report: ImportReport, dry_run: bool
) -> dict[str, int | None]:
    service = CategoryService(session)
    existing = {c.key: c.id for c in service.list_categories(project_id)} if project_id else {}
    wanted: dict[str, tuple[str, str]] = {}
    for item in items:
        for key in item.category_keys:
            if key in item.category_defs:
                wanted.setdefault(key, item.category_defs[key])
    for item in items:
        for key in item.category_keys:
            wanted.setdefault(key, (key, f"Imported from markdown Category gates ({key})"))
    resolved: dict[str, int | None] = {}
    for key in sorted(wanted):
        if key in existing:
            resolved[key] = existing[key]
            report.note("unchanged", f"category {key}")
            continue
        report.note("create", f"category {key}")
        resolved[key] = None if dry_run else service.create_category(project_id, key, *wanted[key]).id
    return resolved


def _sync_sprint(
    session: Session, project_id: int | None, item: MarkdownItem, report: ImportReport, dry_run: bool
) -> int | None:
    service = SprintService(session)
    label = f"sprint {display_id(item.sequence)} {item.title}"
    existing = service.get_sprint_by_sequence(project_id, item.sequence) if project_id else None
    if existing is None:
        report.note("create", label)
        if dry_run:
            return None
        created = service.create_sprint(
            project_id, item.title, item.summary, sequence=item.sequence, status=item.status
        )
        return created.id
    if existing.status.value != item.status and item.status == SprintStatus.CLOSED.value:
        report.note("update", f"{label} (status -> closed)")
        if not dry_run:
            service.close_sprint(existing.id)
    else:
        report.note("unchanged", label)
    return existing.id


def _sync_issue(
    session: Session,
    project_id: int | None,
    item: MarkdownItem,
    categories: dict[str, int | None],
    sprints: dict[int, int | None],
    report: ImportReport,
    dry_run: bool,
) -> None:
    service = IssueService(session)
    label = f"issue {display_id(item.sequence)} {item.title}"
    category_id = categories.get(item.category_keys[0]) if item.category_keys else None
    sprint_id = sprints.get(item.sprint_sequence) if item.sprint_sequence is not None else None
    existing = (service.repo.get_issue_by_sequence(project_id, item.sequence)) if project_id else None
    if existing is None:
        report.note("create", f"{label} [{item.status}]")
        if dry_run:
            return
        issue = service.create_issue(
            project_id,
            item.title,
            item.acceptance_criteria,
            summary=item.summary,
            category_id=category_id,
            labels=item.category_keys,
            sequence=item.sequence,
        )
        if sprint_id is not None:
            SprintService(session).add_issue(sprint_id, issue.id)
        _apply_status(service, issue.id, issue.status.value, item)
        return

    changes: list[str] = []
    if (existing.title, existing.acceptance_criteria, existing.category_id) != (
        item.title,
        item.acceptance_criteria,
        category_id,
    ):
        changes.append("details")
    in_sprint = sprint_id is not None and any(
        m.issue_id == existing.id for m in SprintService(session).list_issues(sprint_id)
    )
    closed = existing.status == IssueStatus.DONE and existing.closed_at is not None
    needs_sprint = sprint_id is not None and not in_sprint and not closed
    if needs_sprint:
        changes.append("sprint")
    if existing.status.value != item.status and not closed:
        changes.append(f"status -> {item.status}")
    if not changes:
        report.note("unchanged", label)
        return
    report.note("update", f"{label} ({', '.join(changes)})")
    if dry_run:
        return
    if "details" in changes:
        service.update_details(existing.id, item.title, item.acceptance_criteria, category_id, actor=IMPORT_LLM)
    status_before = existing.status.value
    if needs_sprint:
        SprintService(session).add_issue(sprint_id, existing.id)
        status_before = IssueStatus.IN_PROGRESS.value
    _apply_status(service, existing.id, status_before, item)


def _apply_status(service: IssueService, issue_id: int, current: str, item: MarkdownItem) -> None:
    if current == item.status:
        return
    service.update_status(
        issue_id,
        item.status,
        originating_llm=item.originating_llm or IMPORT_LLM,
        closed_by=IMPORT_LLM,
        close_note=f"Imported from {item.path.name}",
        actor=IMPORT_LLM,
    )
