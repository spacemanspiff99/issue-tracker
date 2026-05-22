from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from issue_tracker.domain.models import Project
from issue_tracker.services.recovery_bundle import RecoveryBundleService
from issue_tracker.services.tracker import DomainError, slugify

GIT_SAFE_EXCLUSIONS = {
    ".env",
    ".dump",
    ".sql",
    ".sqlite",
    ".db",
    ".webm",
    ".mp3",
    ".wav",
    ".png",
    ".jpg",
    ".jpeg",
    ".key",
    ".crt",
}
ARTIFACT_BACKUP_KINDS = {
    "postgres-dump",
    "raw-audio",
    "screenshot",
    "generated-export",
    "local-artifact",
}


@dataclass(frozen=True)
class BackupTargetResult:
    status: str
    target_path: str
    snapshot_path: str
    blocked_reason: str | None
    provenance: dict[str, Any]
    next_action: str


@dataclass(frozen=True)
class ArtifactBackupResult:
    status: str
    backend: str
    archive_id: str | None
    blocked_reason: str | None
    manifest: dict[str, Any]
    next_action: str


class VibecodingBackupService:
    def __init__(self, session: Session):
        self.session = session

    def plan_target_paths(self, project_id: int, backup_date: date | None = None) -> dict[str, str]:
        project = self.session.get(Project, project_id)
        if project is None:
            raise DomainError("Project was not found")
        slug = slugify(project.id, project.name).split("-", 1)[1]
        dated = (backup_date or date.today()).isoformat()
        base = f"projects/{slug}/tracker-backups"
        return {"latest": f"{base}/latest", "snapshot": f"{base}/snapshots/{dated}"}

    def publish_bundle(
        self,
        project_id: int,
        bundle_dir: Path,
        vibecoding_root: Path | None = None,
        actor: str = "codex",
        dry_run: bool = True,
        token_env: str = "VIBECODING_MIRROR_TOKEN",
    ) -> BackupTargetResult:
        validation = RecoveryBundleService(self.session).validate_bundle(bundle_dir)
        paths = self.plan_target_paths(project_id)
        project = self.session.get(Project, project_id)
        if project is None:
            raise DomainError("Project was not found")
        provenance = {
            "source_repo": project.repo_url,
            "source_branch": project.default_branch,
            "tracker_project_id": project.id,
            "actor": actor,
            "export_checksum": self._manifest_digest(bundle_dir),
            "workflow_run": os.environ.get("GITHUB_RUN_ID"),
            "created_at": datetime.now(UTC).isoformat(),
        }
        if not validation.ok:
            return BackupTargetResult(
                "blocked",
                paths["latest"],
                paths["snapshot"],
                "Recovery bundle validation failed before publication",
                provenance,
                "Re-export and validate the sanitized bundle before publishing to vibecoding.",
            )
        if not os.environ.get(token_env):
            return BackupTargetResult(
                "blocked",
                paths["latest"],
                paths["snapshot"],
                f"{token_env} is not available",
                provenance,
                f"Provide {token_env} with access to the vibecoding repository, then rerun publication.",
            )
        if dry_run:
            return BackupTargetResult(
                "dry-run",
                paths["latest"],
                paths["snapshot"],
                None,
                provenance,
                "Review the publication plan, then rerun with dry_run=false from an authenticated environment.",
            )
        if vibecoding_root is None:
            return BackupTargetResult(
                "blocked",
                paths["latest"],
                paths["snapshot"],
                "No vibecoding checkout path was provided",
                provenance,
                "Clone vibecoding locally or use the PR workflow with repository access.",
            )
        root = vibecoding_root.resolve()
        latest = root / paths["latest"]
        snapshot = root / paths["snapshot"]
        self._copy_sanitized(bundle_dir, latest)
        self._copy_sanitized(bundle_dir, snapshot)
        for target in (latest, snapshot):
            (target / "publication-provenance.json").write_text(
                json.dumps(provenance, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return BackupTargetResult(
            "published",
            paths["latest"],
            paths["snapshot"],
            None,
            provenance,
            "Open a review PR.",
        )

    def _copy_sanitized(self, source: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            if any(part.startswith(".") and part != ".well-known" for part in relative.parts):
                continue
            if path.suffix.lower() in GIT_SAFE_EXCLUSIONS:
                raise DomainError(f"Unsafe artifact file cannot be published to Git: {relative.as_posix()}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

    @staticmethod
    def _manifest_digest(bundle_dir: Path) -> str | None:
        manifest = bundle_dir / "manifest.json"
        if not manifest.exists():
            return None
        import hashlib

        return hashlib.sha256(manifest.read_bytes()).hexdigest()


class ArtifactBackupAdapter:
    def prepare_backup(
        self,
        artifact_paths: list[Path],
        backend: str = "restic",
        repository: str | None = None,
        password_env: str = "RESTIC_PASSWORD",
        execute: bool = False,
    ) -> ArtifactBackupResult:
        manifests = [self._artifact_metadata(path) for path in artifact_paths]
        if backend not in {"restic", "borg", "rclone"}:
            return self._blocked(backend, f"Unsupported encrypted artifact backend {backend!r}", manifests)
        if not shutil.which(backend):
            return self._blocked(backend, f"{backend} is not installed on this host", manifests)
        if backend == "restic" and not repository:
            return self._blocked(backend, "RESTIC_REPOSITORY or an explicit repository is required", manifests)
        if backend == "restic" and not os.environ.get(password_env):
            return self._blocked(backend, f"{password_env} is not available", manifests)
        archive_id = f"dry-run:{backend}:{len(manifests)}"
        if execute:
            command = [backend, "backup", *[str(path) for path in artifact_paths]]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            if result.returncode != 0:
                return self._blocked(backend, "Encrypted artifact backup command failed", manifests)
            archive_id = f"{backend}:executed"
        return ArtifactBackupResult(
            "ready" if not execute else "verified",
            backend,
            archive_id,
            None,
            {"backend": backend, "repository": repository, "artifacts": manifests},
            "Store only this manifest in Issue Tracker; keep encrypted archives outside Git.",
        )

    def _blocked(self, backend: str, reason: str, artifacts: list[dict[str, Any]]) -> ArtifactBackupResult:
        return ArtifactBackupResult(
            "blocked",
            backend,
            None,
            reason,
            {"backend": backend, "artifacts": artifacts},
            f"Owner action required: {reason}.",
        )

    @staticmethod
    def _artifact_metadata(path: Path) -> dict[str, Any]:
        suffix = path.suffix.lower()
        kind = "local-artifact"
        if suffix in {".dump", ".sql"}:
            kind = "postgres-dump"
        elif suffix in {".webm", ".mp3", ".wav"}:
            kind = "raw-audio"
        elif suffix in {".png", ".jpg", ".jpeg"}:
            kind = "screenshot"
        elif "exports" in path.parts:
            kind = "generated-export"
        return {
            "path_hint": path.name,
            "kind": kind if kind in ARTIFACT_BACKUP_KINDS else "local-artifact",
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
