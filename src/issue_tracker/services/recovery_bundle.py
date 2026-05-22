from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from issue_tracker import __version__
from issue_tracker.domain.models import (
    Category,
    GuidanceAuditEntry,
    GuidanceBranch,
    GuidanceDrift,
    GuidanceIngestedEvent,
    GuidanceSnapshot,
    GuidanceSource,
    GuidanceSyncProposal,
    GuidanceSyncRun,
    Issue,
    IssueDependency,
    IssueLogEntry,
    LinkedPR,
    Project,
    Sprint,
    SprintIssue,
)
from issue_tracker.services.tracker import DomainError, display_id, slugify

SCHEMA_VERSION = "recovery-bundle-v1"
DEFAULT_BUNDLE_ROOT = Path("exports/recovery-bundles")
REDACTED = "[redacted-local-or-secret-value]"
SENSITIVE_KEY_PARTS = {
    "password",
    "password_hash",
    "secret",
    "token",
    "session",
    "credential",
    "private_key",
    "audio_path",
}
LOCAL_ARTIFACT_PATTERNS = [
    re.compile(r"exports/voice-feedback/[^\s`)]+"),
    re.compile(r"exports/browser-uat-[^\s`)]+"),
    re.compile(r"exports/local-https/[^\s`)]+"),
    re.compile(r"backups/[^\s`)]+"),
    re.compile(r"\.env(?:\.[A-Za-z0-9_-]+)?"),
]


@dataclass(frozen=True)
class BundleValidation:
    ok: bool
    status: str
    project_name: str
    manifest_path: Path
    errors: list[str]
    counts: dict[str, int]


class RecoveryBundleService:
    def __init__(self, session: Session):
        self.session = session

    def export_bundle(self, project_id: int, output_dir: Path) -> Path:
        project = self.session.get(Project, project_id)
        if project is None:
            raise DomainError("Project was not found")
        bundle_dir = output_dir.resolve()
        bundle_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, Any] = {
            "project.json": self._project_payload(project),
            "categories.json": [
                self._category_payload(category)
                for category in self.session.query(Category).filter_by(project_id=project_id).order_by(Category.key)
            ],
            "dependencies.json": [
                self._dependency_payload(dependency)
                for dependency in self.session.query(IssueDependency)
                .filter_by(project_id=project_id)
                .order_by(IssueDependency.id)
            ],
            "sprint_issues.json": [
                self._sprint_issue_payload(membership)
                for membership in self.session.query(SprintIssue)
                .join(Sprint, Sprint.id == SprintIssue.sprint_id)
                .filter(Sprint.project_id == project_id)
                .order_by(Sprint.sequence, SprintIssue.sort_order)
            ],
        }
        jsonl_files: dict[str, list[dict[str, Any]]] = {
            "issues.jsonl": [
                self._issue_payload(issue)
                for issue in self.session.query(Issue).filter_by(project_id=project_id).order_by(Issue.sequence)
            ],
            "sprints.jsonl": [
                self._sprint_payload(sprint)
                for sprint in self.session.query(Sprint).filter_by(project_id=project_id).order_by(Sprint.sequence)
            ],
            "issue_logs.jsonl": [
                self._issue_log_payload(entry)
                for entry in self.session.query(IssueLogEntry)
                .filter_by(project_id=project_id)
                .order_by(IssueLogEntry.id)
            ],
            "linked_references.jsonl": [
                self._linked_reference_payload(reference)
                for reference in self.session.query(LinkedPR)
                .join(Issue, Issue.id == LinkedPR.issue_id, isouter=True)
                .filter(Issue.project_id == project_id)
                .order_by(LinkedPR.id)
            ],
            "guidance/sources.jsonl": [
                self._guidance_source_payload(source)
                for source in self.session.query(GuidanceSource)
                .filter_by(project_id=project_id)
                .order_by(GuidanceSource.id)
            ],
            "guidance/branches.jsonl": self._guidance_branch_payloads(project_id),
            "guidance/snapshots.jsonl": self._guidance_snapshot_payloads(project_id),
            "guidance/drifts.jsonl": [
                self._guidance_drift_payload(drift)
                for drift in self.session.query(GuidanceDrift)
                .filter_by(project_id=project_id)
                .order_by(GuidanceDrift.id)
            ],
            "guidance/proposals.jsonl": [
                self._guidance_proposal_payload(proposal)
                for proposal in self.session.query(GuidanceSyncProposal)
                .filter_by(project_id=project_id)
                .order_by(GuidanceSyncProposal.id)
            ],
            "guidance/runs.jsonl": [
                self._guidance_run_payload(run)
                for run in self.session.query(GuidanceSyncRun)
                .filter_by(project_id=project_id)
                .order_by(GuidanceSyncRun.id)
            ],
            "guidance/audit.jsonl": [
                self._guidance_audit_payload(entry)
                for entry in self.session.query(GuidanceAuditEntry)
                .filter_by(project_id=project_id)
                .order_by(GuidanceAuditEntry.id)
            ],
            "guidance/ingested_events.jsonl": [
                self._guidance_ingested_event_payload(event)
                for event in self.session.query(GuidanceIngestedEvent)
                .filter_by(project_id=project_id)
                .order_by(GuidanceIngestedEvent.id)
            ],
        }

        checksums: dict[str, str] = {}
        for relative, payload in files.items():
            path = bundle_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._sanitize(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
            checksums[relative] = self._sha256(path)
        for relative, rows in jsonl_files.items():
            path = bundle_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "".join(json.dumps(self._sanitize(row), sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
            checksums[relative] = self._sha256(path)

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "app_version": __version__,
            "exported_at": datetime.now(UTC).isoformat(),
            "project": {
                "id": project.id,
                "sequence_next": project.next_sequence,
                "name": project.name,
                "slug": self._project_slug(project),
            },
            "source": {
                "git_commit": self._git_commit(),
                "alembic_revision": self._alembic_revision(),
            },
            "counts": self._counts(project_id),
            "files": [{"path": path, "sha256": digest} for path, digest in sorted(checksums.items())],
            "excluded": [
                "password hashes",
                "sessions",
                "secret or token values",
                "raw audio",
                "screenshots",
                "local HTTPS certificates",
                "database dumps",
                "environment files",
                "cache files",
            ],
        }
        manifest_path = bundle_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest_path

    def export_latest_bundle(self, project_id: int, root: Path = DEFAULT_BUNDLE_ROOT) -> Path:
        project = self.session.get(Project, project_id)
        if project is None:
            raise DomainError("Project was not found")
        return self.export_bundle(project_id, root / self._project_slug(project) / "latest")

    def validate_bundle(self, bundle_dir: Path) -> BundleValidation:
        manifest_path = bundle_dir / "manifest.json"
        errors: list[str] = []
        if not manifest_path.exists():
            return BundleValidation(False, "missing", "", manifest_path, ["manifest.json is missing"], {})
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return BundleValidation(False, "invalid", "", manifest_path, [f"manifest is not valid JSON: {exc}"], {})
        if manifest.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"unsupported schema_version {manifest.get('schema_version')!r}")
        for item in manifest.get("files", []):
            relative = item.get("path")
            expected = item.get("sha256")
            if not relative or not expected:
                errors.append("manifest file entry is incomplete")
                continue
            path = bundle_dir / relative
            if not path.exists():
                errors.append(f"{relative} is missing")
                continue
            actual = self._sha256(path)
            if actual != expected:
                errors.append(f"{relative} checksum mismatch")
        project = manifest.get("project", {})
        counts = manifest.get("counts", {})
        return BundleValidation(
            ok=not errors,
            status="verified" if not errors else "failed",
            project_name=str(project.get("name") or ""),
            manifest_path=manifest_path,
            errors=errors,
            counts={str(key): int(value) for key, value in counts.items()},
        )

    def restore_dry_run(self, bundle_dir: Path) -> dict[str, Any]:
        validation = self.validate_bundle(bundle_dir)
        if not validation.ok:
            return {
                "ok": False,
                "status": validation.status,
                "errors": validation.errors,
                "would_create": {},
                "would_require_category_mapping": False,
            }
        project_payload = json.loads((bundle_dir / "project.json").read_text(encoding="utf-8"))
        categories = json.loads((bundle_dir / "categories.json").read_text(encoding="utf-8"))
        return {
            "ok": True,
            "status": "dry-run",
            "project_name": project_payload["name"],
            "would_create": validation.counts,
            "would_require_category_mapping": bool(categories),
            "errors": [],
        }

    def backup_health(self, project_id: int, root: Path = DEFAULT_BUNDLE_ROOT) -> dict[str, Any]:
        project = self.session.get(Project, project_id)
        if project is None:
            raise DomainError("Project was not found")
        latest = root / self._project_slug(project) / "latest"
        validation = self.validate_bundle(latest)
        next_action = "Run issue-tracker export-recovery-bundle to create the first portable backup."
        if validation.ok:
            next_action = "Run restore-recovery-bundle --dry-run after significant tracker changes."
        elif validation.status == "failed":
            next_action = "Re-export the recovery bundle or inspect checksum failures."
        return {
            "project_id": project_id,
            "status": "verified" if validation.ok else validation.status,
            "bundle": str(latest),
            "manifest": str(validation.manifest_path),
            "counts": validation.counts,
            "errors": validation.errors,
            "next": next_action,
        }

    def _project_payload(self, project: Project) -> dict[str, Any]:
        return {
            "id": project.id,
            "name": project.name,
            "repo_url": project.repo_url,
            "default_branch": project.default_branch,
            "tracker_path_hint": project.tracker_path_hint,
            "rules_path_hint": project.rules_path_hint,
            "active": project.active,
            "next_sequence": project.next_sequence,
            "created_at": self._iso(project.created_at),
        }

    def _category_payload(self, category: Category) -> dict[str, Any]:
        return {
            "id": category.id,
            "key": category.key,
            "name": category.name,
            "description": category.description,
            "checklist": category.checklist,
        }

    def _issue_payload(self, issue: Issue) -> dict[str, Any]:
        return {
            "id": issue.id,
            "sequence": issue.sequence,
            "display_id": display_id(issue.sequence),
            "slug": issue.slug,
            "title": issue.title,
            "status": issue.status.value,
            "priority": issue.priority,
            "labels": issue.labels,
            "category_id": issue.category_id,
            "summary": issue.summary,
            "proposed_approach": issue.proposed_approach,
            "acceptance_criteria": issue.acceptance_criteria,
            "originating_llm": issue.originating_llm,
            "closed_by": issue.closed_by,
            "close_note": issue.close_note,
            "created_at": self._iso(issue.created_at),
            "closed_at": self._iso(issue.closed_at),
        }

    def _dependency_payload(self, dependency: IssueDependency) -> dict[str, Any]:
        return {
            "id": dependency.id,
            "blocker_issue_id": dependency.blocker_issue_id,
            "blocked_issue_id": dependency.blocked_issue_id,
            "created_at": self._iso(dependency.created_at),
        }

    def _sprint_payload(self, sprint: Sprint) -> dict[str, Any]:
        return {
            "id": sprint.id,
            "sequence": sprint.sequence,
            "display_id": display_id(sprint.sequence),
            "slug": sprint.slug,
            "goal": sprint.goal,
            "context": sprint.context,
            "status": sprint.status.value,
            "next_sprint_id": sprint.next_sprint_id,
            "created_at": self._iso(sprint.created_at),
            "closed_at": self._iso(sprint.closed_at),
        }

    def _sprint_issue_payload(self, membership: SprintIssue) -> dict[str, Any]:
        return {
            "id": membership.id,
            "sprint_id": membership.sprint_id,
            "issue_id": membership.issue_id,
            "phase": membership.phase,
            "sort_order": membership.sort_order,
            "status": membership.status.value,
        }

    def _issue_log_payload(self, entry: IssueLogEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "issue_id": entry.issue_id,
            "category_id": entry.category_id,
            "root_cause": entry.root_cause,
            "prevention_added": entry.prevention_added,
            "created_at": self._iso(entry.created_at),
        }

    def _linked_reference_payload(self, reference: LinkedPR) -> dict[str, Any]:
        return {
            "id": reference.id,
            "issue_id": reference.issue_id,
            "sprint_id": reference.sprint_id,
            "provider": reference.provider,
            "repo": reference.repo,
            "pr_number": reference.pr_number,
            "url": reference.url,
            "merge_status": reference.merge_status,
        }

    def _guidance_source_payload(self, source: GuidanceSource) -> dict[str, Any]:
        return {
            "id": source.id,
            "name": source.name,
            "repo_url": source.repo_url,
            "default_branch": source.default_branch,
            "vibecoding_target_path": source.vibecoding_target_path,
            "tracked_paths": source.tracked_paths,
            "scan_status": source.scan_status,
            "created_at": self._iso(source.created_at),
        }

    def _guidance_branch_payloads(self, project_id: int) -> list[dict[str, Any]]:
        rows = (
            self.session.query(GuidanceBranch)
            .join(GuidanceSource, GuidanceSource.id == GuidanceBranch.source_id)
            .filter(GuidanceSource.project_id == project_id)
            .order_by(GuidanceBranch.id)
        )
        return [
            {
                "id": branch.id,
                "source_id": branch.source_id,
                "name": branch.name,
                "commit_sha": branch.commit_sha,
                "is_default": branch.is_default,
                "scan_status": branch.scan_status,
                "scanned_at": self._iso(branch.scanned_at),
            }
            for branch in rows
        ]

    def _guidance_snapshot_payloads(self, project_id: int) -> list[dict[str, Any]]:
        rows = (
            self.session.query(GuidanceSnapshot)
            .join(GuidanceSource, GuidanceSource.id == GuidanceSnapshot.source_id)
            .filter(GuidanceSource.project_id == project_id)
            .order_by(GuidanceSnapshot.id)
        )
        return [
            {
                "id": snapshot.id,
                "source_id": snapshot.source_id,
                "branch_name": snapshot.branch_name,
                "commit_sha": snapshot.commit_sha,
                "path": snapshot.path,
                "content_hash": snapshot.content_hash,
                "size_bytes": snapshot.size_bytes,
                "scan_status": snapshot.scan_status,
                "actor": snapshot.actor,
                "scanned_at": self._iso(snapshot.scanned_at),
            }
            for snapshot in rows
        ]

    def _guidance_drift_payload(self, drift: GuidanceDrift) -> dict[str, Any]:
        return {
            "id": drift.id,
            "source_id": drift.source_id,
            "left_snapshot_id": drift.left_snapshot_id,
            "right_snapshot_id": drift.right_snapshot_id,
            "path": drift.path,
            "drift_type": drift.drift_type,
            "severity": drift.severity,
            "summary": drift.summary,
            "recommended_action": drift.recommended_action,
            "status": drift.status,
            "created_at": self._iso(drift.created_at),
        }

    def _guidance_proposal_payload(self, proposal: GuidanceSyncProposal) -> dict[str, Any]:
        return {
            "id": proposal.id,
            "drift_id": proposal.drift_id,
            "issue_id": proposal.issue_id,
            "action": proposal.action,
            "status": proposal.status,
            "owner": proposal.owner,
            "verification_command": proposal.verification_command,
            "approval_text": proposal.approval_text,
            "created_at": self._iso(proposal.created_at),
        }

    def _guidance_run_payload(self, run: GuidanceSyncRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "proposal_id": run.proposal_id,
            "status": run.status,
            "logs": run.logs,
            "pr_url": run.pr_url,
            "branch_name": run.branch_name,
            "commit_sha": run.commit_sha,
            "verification_status": run.verification_status,
            "created_at": self._iso(run.created_at),
        }

    def _guidance_audit_payload(self, entry: GuidanceAuditEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "event_type": entry.event_type,
            "summary": entry.summary,
            "actor": entry.actor,
            "related_type": entry.related_type,
            "related_id": entry.related_id,
            "details": entry.details,
            "created_at": self._iso(entry.created_at),
        }

    def _guidance_ingested_event_payload(self, event: GuidanceIngestedEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "repo": event.repo,
            "branch": event.branch,
            "commit_sha": event.commit_sha,
            "path_set_hash": event.path_set_hash,
            "event_type": event.event_type,
            "status": event.status,
            "created_at": self._iso(event.created_at),
        }

    def _counts(self, project_id: int) -> dict[str, int]:
        source_ids = [
            source_id for (source_id,) in self.session.query(GuidanceSource.id).filter_by(project_id=project_id)
        ]
        return {
            "categories": self.session.query(Category).filter_by(project_id=project_id).count(),
            "issues": self.session.query(Issue).filter_by(project_id=project_id).count(),
            "dependencies": self.session.query(IssueDependency).filter_by(project_id=project_id).count(),
            "sprints": self.session.query(Sprint).filter_by(project_id=project_id).count(),
            "issue_logs": self.session.query(IssueLogEntry).filter_by(project_id=project_id).count(),
            "guidance_sources": len(source_ids),
            "guidance_snapshots": self.session.query(GuidanceSnapshot)
            .filter(GuidanceSnapshot.source_id.in_(source_ids))
            .count()
            if source_ids
            else 0,
            "guidance_drifts": self.session.query(GuidanceDrift).filter_by(project_id=project_id).count(),
            "guidance_proposals": self.session.query(GuidanceSyncProposal).filter_by(project_id=project_id).count(),
        }

    def _alembic_revision(self) -> str | None:
        try:
            return self.session.execute(text("select version_num from alembic_version")).scalar_one_or_none()
        except Exception:
            return None

    @staticmethod
    def _git_commit() -> str | None:
        try:
            return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    @staticmethod
    def _project_slug(project: Project) -> str:
        return slugify(project.id, project.name).split("-", 1)[1]

    def _sanitize(self, value: Any, key: str = "") -> Any:
        if any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
            return REDACTED
        if isinstance(value, dict):
            return {item_key: self._sanitize(item_value, item_key) for item_key, item_value in value.items()}
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        if isinstance(value, str):
            clean = value
            for pattern in LOCAL_ARTIFACT_PATTERNS:
                clean = pattern.sub(REDACTED, clean)
            return clean
        return value
