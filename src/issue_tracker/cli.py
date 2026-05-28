from __future__ import annotations

import argparse
import ipaddress
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
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
from issue_tracker.services.recovery_bundle import RecoveryBundleService
from issue_tracker.services.rule_relevance import RuleRelevanceService
from issue_tracker.services.tracker import CategoryService, IssueService, ProjectService


def _write_private_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def _write_cert(path: Path, cert: x509.Certificate) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _subject(name: str) -> x509.Name:
    return x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Issue Tracker Local Development"),
            x509.NameAttribute(NameOID.COMMON_NAME, name),
        ]
    )


def _subject_alt_names(hosts: list[str]) -> x509.SubjectAlternativeName:
    names: list[x509.GeneralName] = []
    for host in sorted(set(hosts)):
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            names.append(x509.DNSName(host))
    return x509.SubjectAlternativeName(names)


def generate_dev_certs(cert_dir: Path, hosts: list[str], valid_days: int, force: bool = False) -> None:
    cert_dir.mkdir(parents=True, exist_ok=True)
    root_key_path = cert_dir / "root-ca.key"
    root_cert_path = cert_dir / "root-ca.crt"
    server_key_path = cert_dir / "server.key"
    server_cert_path = cert_dir / "server.crt"
    paths = [root_key_path, root_cert_path, server_key_path, server_cert_path]
    existing = [path for path in paths if path.exists()]
    if existing and not force:
        names = ", ".join(str(path) for path in existing)
        raise SystemExit(f"Certificate files already exist: {names}. Pass --force to replace them.")

    now = datetime.now(UTC)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    root_subject = _subject("Issue Tracker Local Dev Root CA")
    root_cert = (
        x509.CertificateBuilder()
        .subject_name(root_subject)
        .issuer_name(root_subject)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_hosts = ["localhost", "127.0.0.1", *hosts]
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(_subject(cert_hosts[0]))
        .issuer_name(root_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(_subject_alt_names(cert_hosts), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=False,
                crl_sign=False,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(root_key, hashes.SHA256())
    )

    _write_private_key(root_key_path, root_key)
    _write_cert(root_cert_path, root_cert)
    _write_private_key(server_key_path, server_key)
    _write_cert(server_cert_path, server_cert)
    print(f"Wrote local HTTPS certs to {cert_dir}")
    print(f"Trust this CA on the remote browser machine: {root_cert_path}")
    print("Start HTTPS with: docker compose -f deployment/docker-compose.local.yml --profile https up -d app-https")


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
            {"root_cause": log.root_cause, "prevention_added": log.prevention_added}
            for log in session.query(IssueLogEntry).filter_by(project_id=project_id).all()
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


def export_recovery_bundle(session: Session, project_id: int, output_dir: Path) -> Path:
    return RecoveryBundleService(session).export_bundle(project_id, output_dir)


def restore_recovery_bundle_dry_run(session: Session, input_dir: Path) -> dict[str, object]:
    return RecoveryBundleService(session).restore_dry_run(input_dir)


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
    bundle = sub.add_parser("export-recovery-bundle")
    bundle.add_argument("project_id", type=int)
    bundle.add_argument("output_dir", type=Path)
    restore_bundle = sub.add_parser("restore-recovery-bundle")
    restore_bundle.add_argument("input_dir", type=Path)
    restore_bundle.add_argument("--dry-run", action="store_true", required=True)
    lint_prompt = sub.add_parser("lint-prompt")
    lint_prompt.add_argument("prompt", type=Path)
    lint_prompt.add_argument("--project-type", action="append", default=["fastapi-jinja-postgres"])
    lint_prompt.add_argument("--changed-path", action="append", default=[])
    lint_prompt.add_argument("--risk", action="append", default=[])
    compile_prompt = sub.add_parser("compile-prompt")
    compile_prompt.add_argument("title")
    compile_prompt.add_argument("--context", default="")
    compile_prompt.add_argument("--acceptance", action="append", default=[])
    compile_prompt.add_argument("--verification", action="append", default=[])
    compile_prompt.add_argument("--stop", default="Record remaining work or close the issue with evidence.")
    compile_prompt.add_argument("--project-type", action="append", default=["fastapi-jinja-postgres"])
    certs = sub.add_parser("generate-dev-certs")
    certs.add_argument("--cert-dir", type=Path, default=Path("exports/local-https"))
    certs.add_argument("--host", action="append", default=[], help="LAN hostname or IP used by remote browsers")
    certs.add_argument("--valid-days", type=int, default=365)
    certs.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "generate-dev-certs":
        generate_dev_certs(args.cert_dir, args.host, args.valid_days, force=args.force)
    else:
        with SessionLocal() as session:
            if args.command == "export-json":
                export_json(session, args.project_id, args.output)
            elif args.command == "import-json":
                project_id = import_json(session, args.input, args.project_name, parse_mapping(args.category_map))
                print(project_id)
            elif args.command == "export-recovery-bundle":
                manifest_path = export_recovery_bundle(session, args.project_id, args.output_dir)
                print(manifest_path)
            elif args.command == "restore-recovery-bundle":
                print(json.dumps(restore_recovery_bundle_dry_run(session, args.input_dir), sort_keys=True))
            elif args.command == "lint-prompt":
                result = RuleRelevanceService().lint_prompt(
                    args.prompt.read_text(encoding="utf-8"),
                    args.project_type,
                    changed_paths=args.changed_path,
                    risk_labels=args.risk,
                )
                print(json.dumps(result.machine, sort_keys=True))
            elif args.command == "compile-prompt":
                print(
                    RuleRelevanceService().compile_prompt(
                        args.title,
                        args.context,
                        args.acceptance,
                        args.verification,
                        args.stop,
                        args.project_type,
                    )
                )


if __name__ == "__main__":
    main()
