from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from issue_tracker.domain.models import (
    GuidanceAuditEntry,
    GuidanceBranch,
    GuidanceDrift,
    GuidanceIngestedEvent,
    GuidanceSnapshot,
    GuidanceSource,
    GuidanceSyncProposal,
    GuidanceSyncRun,
    Project,
)
from issue_tracker.services.tracker import DomainError

DRIFT_TYPES = {
    "in-sync",
    "stale",
    "local-only",
    "target-only",
    "deleted",
    "renamed",
    "conflict",
    "protected-change",
    "auth-blocked",
    "scan-incomplete",
}

EXCLUDED_PARTS = {".git", ".env", "exports", "backups", "__pycache__", ".pytest_cache"}


@dataclass(frozen=True)
class FileSnapshot:
    path: str
    content_hash: str
    size_bytes: int


class GuidanceSyncService:
    def __init__(self, session: Session):
        self.session = session

    def configure_source(
        self,
        project_id: int,
        name: str,
        repo_url: str,
        tracked_paths: list[str],
        default_branch: str = "main",
        vibecoding_target_path: str | None = None,
    ) -> GuidanceSource:
        if not name.strip() or not repo_url.strip():
            raise DomainError("Guidance source name and repo URL are required")
        if not tracked_paths:
            raise DomainError("At least one tracked guidance path is required")
        project = self.session.get(Project, project_id)
        if project is None:
            raise DomainError("Project was not found")
        source = self.session.scalar(
            select(GuidanceSource).where(GuidanceSource.project_id == project_id, GuidanceSource.name == name.strip())
        )
        if source is None:
            source = GuidanceSource(project_id=project_id, name=name.strip(), repo_url=repo_url.strip())
            self.session.add(source)
        source.default_branch = default_branch.strip() or "main"
        source.vibecoding_target_path = vibecoding_target_path.strip() if vibecoding_target_path else None
        source.tracked_paths = {"paths": [path.strip() for path in tracked_paths if path.strip()]}
        source.scan_status = "configured"
        self.session.commit()
        return source

    def list_branches(self, repo_path: Path) -> list[str]:
        result = self._git(repo_path, ["branch", "--format", "%(refname:short)"])
        return [line.strip() for line in result.splitlines() if line.strip()]

    def scan_source(self, source_id: int, repo_path: Path, branch_name: str | None = None) -> list[GuidanceSnapshot]:
        source = self.session.get(GuidanceSource, source_id)
        if source is None:
            raise DomainError("Guidance source was not found")
        branch = branch_name or source.default_branch
        repo_root = repo_path.resolve()
        if not repo_root.exists():
            source.scan_status = "auth-blocked"
            self.session.commit()
            return []
        try:
            commit_sha = self._git(repo_root, ["rev-parse", branch]).strip()
        except DomainError:
            commit_sha = None
            source.scan_status = "scan-incomplete"
        files = self._collect_files(repo_root, list(source.tracked_paths.get("paths", [])))
        snapshots = []
        for item in files:
            snapshot = GuidanceSnapshot(
                source_id=source.id,
                branch_name=branch,
                commit_sha=commit_sha,
                path=item.path,
                content_hash=item.content_hash,
                size_bytes=item.size_bytes,
                scan_status="ok",
            )
            self.session.add(snapshot)
            snapshots.append(snapshot)
        branch_status = "ok" if files else source.scan_status
        self._upsert_branch(source.id, branch, commit_sha, branch == source.default_branch, branch_status)
        if files:
            source.scan_status = "ok"
        self.session.commit()
        return snapshots

    def classify_drift(
        self,
        project_id: int,
        path: str,
        source_id: int | None = None,
        left_hash: str | None = None,
        right_hash: str | None = None,
        left_exists: bool = True,
        right_exists: bool = True,
        protected: bool = False,
        scan_status: str = "ok",
    ) -> GuidanceDrift:
        if scan_status in {"auth-blocked", "scan-incomplete"}:
            drift_type = scan_status
            action = "investigate"
        elif not left_exists and right_exists:
            drift_type = "target-only"
            action = "investigate"
        elif left_exists and not right_exists:
            drift_type = "local-only"
            action = "copy"
        elif protected and left_hash != right_hash:
            drift_type = "protected-change"
            action = "investigate"
        elif left_hash == right_hash:
            drift_type = "in-sync"
            action = "skip"
        else:
            drift_type = "stale"
            action = "merge-needed"
        if drift_type not in DRIFT_TYPES:
            raise DomainError("Unsupported drift type")
        drift = GuidanceDrift(
            project_id=project_id,
            source_id=source_id,
            path=path,
            drift_type=drift_type,
            severity="high" if drift_type in {"protected-change", "auth-blocked", "scan-incomplete"} else "normal",
            summary=f"{path}: {drift_type}",
            recommended_action=action,
        )
        self.session.add(drift)
        self.session.commit()
        return drift

    def compare_snapshot_sets(
        self,
        project_id: int,
        left: dict[str, str],
        right: dict[str, str],
        source_id: int | None = None,
        protected_paths: set[str] | None = None,
    ) -> list[GuidanceDrift]:
        protected_paths = protected_paths or set()
        drifts: list[GuidanceDrift] = []
        left_only = {path: digest for path, digest in left.items() if path not in right}
        right_only = {path: digest for path, digest in right.items() if path not in left}
        matched_right_paths: set[str] = set()
        for left_path, left_hash in left_only.items():
            renamed_path = next(
                (right_path for right_path, right_hash in right_only.items() if right_hash == left_hash),
                None,
            )
            if renamed_path:
                matched_right_paths.add(renamed_path)
                drifts.append(
                    self._create_drift(
                        project_id,
                        f"{left_path} -> {renamed_path}",
                        "renamed",
                        "normal",
                        "rename",
                        source_id=source_id,
                    )
                )
            else:
                drifts.append(
                    self.classify_drift(
                        project_id,
                        left_path,
                        source_id=source_id,
                        left_hash=left_hash,
                        right_hash=None,
                        right_exists=False,
                    )
                )
        for right_path, right_hash in right_only.items():
            if right_path in matched_right_paths:
                continue
            drifts.append(
                self.classify_drift(
                    project_id,
                    right_path,
                    source_id=source_id,
                    left_hash=None,
                    right_hash=right_hash,
                    left_exists=False,
                )
            )
        for path in sorted(set(left) & set(right)):
            drifts.append(
                self.classify_drift(
                    project_id,
                    path,
                    source_id=source_id,
                    left_hash=left[path],
                    right_hash=right[path],
                    protected=path in protected_paths,
                )
            )
        return drifts

    def _create_drift(
        self,
        project_id: int,
        path: str,
        drift_type: str,
        severity: str,
        recommended_action: str,
        source_id: int | None = None,
    ) -> GuidanceDrift:
        drift = GuidanceDrift(
            project_id=project_id,
            source_id=source_id,
            path=path,
            drift_type=drift_type,
            severity=severity,
            summary=f"{path}: {drift_type}",
            recommended_action=recommended_action,
        )
        self.session.add(drift)
        self.session.commit()
        return drift

    def create_proposal(
        self,
        project_id: int,
        drift_id: int,
        action: str,
        issue_id: int | None,
        owner: str,
        verification_command: str,
    ) -> GuidanceSyncProposal:
        if not issue_id or not verification_command.strip():
            raise DomainError("Proposal requires linked issue and verification command")
        existing = self.session.scalar(
            select(GuidanceSyncProposal).where(
                GuidanceSyncProposal.project_id == project_id,
                GuidanceSyncProposal.drift_id == drift_id,
                GuidanceSyncProposal.action == action,
            )
        )
        if existing is not None:
            return existing
        proposal = GuidanceSyncProposal(
            project_id=project_id,
            drift_id=drift_id,
            issue_id=issue_id,
            action=action,
            owner=owner.strip() or None,
            verification_command=verification_command.strip(),
        )
        self.session.add(proposal)
        self.session.flush()
        self.record_audit(
            project_id,
            "proposal",
            f"Created {action} proposal",
            related_type="proposal",
            related_id=proposal.id,
        )
        self.session.commit()
        return proposal

    def move_proposal_ready(self, proposal_id: int, approval_text: str = "") -> GuidanceSyncProposal:
        proposal = self.session.get(GuidanceSyncProposal, proposal_id)
        if proposal is None:
            raise DomainError("Proposal was not found")
        drift = self.session.get(GuidanceDrift, proposal.drift_id) if proposal.drift_id else None
        protected_without_approval = (
            drift
            and drift.drift_type == "protected-change"
            and "approve protected guidance" not in approval_text.lower()
        )
        if protected_without_approval:
            raise DomainError("Protected guidance proposals require explicit approval text")
        proposal.approval_text = approval_text.strip() or None
        proposal.status = "ready"
        self.record_audit(
            proposal.project_id,
            "proposal-ready",
            f"Proposal {proposal.id} moved to ready",
            related_type="proposal",
            related_id=proposal.id,
        )
        self.session.commit()
        return proposal

    def execute_proposal(
        self,
        proposal_id: int,
        actor: str,
        direct_push_allowed: bool = False,
        dry_run: bool = True,
    ) -> GuidanceSyncRun:
        proposal = self.session.get(GuidanceSyncProposal, proposal_id)
        if proposal is None:
            raise DomainError("Proposal was not found")
        if proposal.status not in {"ready", "approved"}:
            raise DomainError("Only ready or approved proposals can be executed")
        if direct_push_allowed:
            raise DomainError("Direct pushes are not allowed for guidance sync execution")
        status = "dry-run" if dry_run else "auth-failure"
        logs = self.pr_body(proposal)
        run = GuidanceSyncRun(
            project_id=proposal.project_id,
            proposal_id=proposal.id,
            status=status,
            logs=logs,
            pr_url="dry-run://guidance-sync" if dry_run else None,
            branch_name=f"guidance-sync/{proposal.id}",
            verification_status="pending",
        )
        self.session.add(run)
        self.session.flush()
        self.record_audit(
            proposal.project_id,
            "execution",
            f"Execution {status} for proposal {proposal.id}",
            actor=actor,
            related_type="run",
            related_id=run.id,
        )
        self.session.commit()
        return run

    def ingest_event(
        self,
        project_id: int,
        repo: str,
        branch: str,
        commit_sha: str,
        paths: list[str],
        event_type: str = "push",
        signature_valid: bool = True,
    ) -> GuidanceIngestedEvent:
        if not signature_valid:
            raise DomainError("Invalid guidance event signature")
        path_set_hash = hashlib.sha256("\n".join(sorted(paths)).encode("utf-8")).hexdigest()
        existing = self.session.scalar(
            select(GuidanceIngestedEvent).where(
                GuidanceIngestedEvent.project_id == project_id,
                GuidanceIngestedEvent.repo == repo,
                GuidanceIngestedEvent.branch == branch,
                GuidanceIngestedEvent.commit_sha == commit_sha,
                GuidanceIngestedEvent.path_set_hash == path_set_hash,
            )
        )
        if existing is not None:
            return existing
        event = GuidanceIngestedEvent(
            project_id=project_id,
            repo=repo,
            branch=branch,
            commit_sha=commit_sha,
            path_set_hash=path_set_hash,
            event_type=event_type,
        )
        self.session.add(event)
        self.session.flush()
        self.record_audit(project_id, "ingestion", f"Ingested {event_type} for {repo}@{commit_sha[:8]}")
        self.session.commit()
        return event

    def record_audit(
        self,
        project_id: int,
        event_type: str,
        summary: str,
        actor: str | None = None,
        related_type: str | None = None,
        related_id: int | None = None,
        details: dict[str, object] | None = None,
    ) -> GuidanceAuditEntry:
        entry = GuidanceAuditEntry(
            project_id=project_id,
            event_type=event_type,
            summary=summary,
            actor=actor,
            related_type=related_type,
            related_id=related_id,
            details=details or {},
        )
        self.session.add(entry)
        return entry

    def rollback_plan(self, run_id: int) -> str:
        run = self.session.get(GuidanceSyncRun, run_id)
        if run is None:
            raise DomainError("Sync run was not found")
        return (
            f"Rollback plan for run {run.id}: inspect branch {run.branch_name or 'unknown'}, "
            f"revert commit {run.commit_sha or 'not-recorded'} if one was created, close or update PR "
            f"{run.pr_url or 'not-created'}, then rerun verification."
        )

    def pr_body(self, proposal: GuidanceSyncProposal) -> str:
        drift = self.session.get(GuidanceDrift, proposal.drift_id) if proposal.drift_id else None
        drift_summary = drift.summary if drift else "No drift linked"
        return (
            f"Guidance Sync proposal {proposal.id}\n\n"
            f"Action: {proposal.action}\n"
            f"Drift: {drift_summary}\n"
            f"Linked tracker issue: {proposal.issue_id}\n"
            f"Verification: {proposal.verification_command}\n"
        )

    def dashboard(self, project_id: int) -> dict[str, object]:
        sources = list(
            self.session.scalars(
                select(GuidanceSource).where(GuidanceSource.project_id == project_id).order_by(GuidanceSource.name)
            )
        )
        drifts = list(
            self.session.scalars(
                select(GuidanceDrift).where(GuidanceDrift.project_id == project_id).order_by(GuidanceDrift.id.desc())
            )
        )
        proposals = list(
            self.session.scalars(
                select(GuidanceSyncProposal)
                .where(GuidanceSyncProposal.project_id == project_id)
                .order_by(GuidanceSyncProposal.id.desc())
            )
        )
        audits = list(
            self.session.scalars(
                select(GuidanceAuditEntry)
                .where(GuidanceAuditEntry.project_id == project_id)
                .order_by(GuidanceAuditEntry.id.desc())
                .limit(20)
            )
        )
        return {
            "sources": sources,
            "drifts": drifts,
            "proposals": proposals,
            "audits": audits,
            "drift_count": len([drift for drift in drifts if drift.status == "open"]),
            "scan_status": "ok" if sources and all(source.scan_status == "ok" for source in sources) else "attention",
        }

    def _collect_files(self, repo_root: Path, tracked_paths: list[str]) -> list[FileSnapshot]:
        snapshots = []
        for tracked in tracked_paths:
            base = (repo_root / tracked).resolve()
            if not self._inside(repo_root, base) or not base.exists():
                continue
            candidates = [base] if base.is_file() else [path for path in base.rglob("*") if path.is_file()]
            for path in candidates:
                relative = path.relative_to(repo_root).as_posix()
                if any(part in EXCLUDED_PARTS for part in path.relative_to(repo_root).parts):
                    continue
                if path.name.endswith((".key", ".crt")):
                    continue
                data = path.read_bytes()
                snapshots.append(FileSnapshot(relative, hashlib.sha256(data).hexdigest(), len(data)))
        return snapshots

    def _upsert_branch(
        self, source_id: int, name: str, commit_sha: str | None, is_default: bool, scan_status: str
    ) -> GuidanceBranch:
        branch = self.session.scalar(
            select(GuidanceBranch).where(GuidanceBranch.source_id == source_id, GuidanceBranch.name == name)
        )
        if branch is None:
            branch = GuidanceBranch(source_id=source_id, name=name)
            self.session.add(branch)
        branch.commit_sha = commit_sha
        branch.is_default = is_default
        branch.scan_status = scan_status
        return branch

    def _git(self, repo_path: Path, args: list[str]) -> str:
        try:
            return subprocess.check_output(["git", "-C", str(repo_path), *args], text=True, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise DomainError("Repository scan failed without exposing credentials") from exc

    @staticmethod
    def _inside(parent: Path, child: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False
