from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CRITICAL_BASELINE = {
    "codex-dogfood",
    "acceptance-criteria",
    "dirty-worktree",
    "verification",
    "closeout-evidence",
    "safety-boundaries",
}
RISK_RULES = {
    "schema": {"schema-migration"},
    "migration": {"schema-migration"},
    "auth": {"auth-secrets"},
    "secrets": {"auth-secrets"},
    "deployment": {"deployment-config"},
    "mcp": {"mcp-contract"},
    "ui": {"ui-provenance"},
    "magicpatterns": {"ui-provenance"},
    "backup": {"backup-safety"},
    "guidance-sync": {"guidance-sync-safety"},
}
RULE_PACKS = {
    "fastapi-jinja-postgres": {"schema-migration", "deployment-config"},
    "mcp-server": {"mcp-contract"},
    "deployment": {"deployment-config"},
    "frontend-ui": {"ui-provenance"},
    "protected-magicpatterns-ui": {"ui-provenance"},
    "documentation-only": {"documentation-durable"},
    "generic-github": {"guidance-sync-safety"},
    "dogfood": {"codex-dogfood", "acceptance-criteria"},
}


@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    title: str
    harness: str
    source_path: str
    project_types: tuple[str, ...] = ()
    file_globs: tuple[str, ...] = ()
    task_types: tuple[str, ...] = ()
    risk_categories: tuple[str, ...] = ()
    priority: int = 100
    critical: bool = False
    dependencies: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    owner: str = "codex"
    version: str = "1.0.0"
    deprecated: bool = False
    content_hash: str | None = None
    branch: str | None = None
    commit_sha: str | None = None


@dataclass(frozen=True)
class EffectiveRule:
    metadata: RuleMetadata
    status: str
    reason: str


@dataclass(frozen=True)
class RuleResolution:
    status: str
    rules: list[EffectiveRule]
    missing_critical: list[str]
    conflicts: list[str]
    explanation: list[str]


@dataclass(frozen=True)
class PromptLintResult:
    status: str
    missing_critical_rules: list[str]
    warnings: list[str]
    errors: list[str]
    machine: dict[str, Any]


@dataclass(frozen=True)
class MissingRuleIncident:
    status: str
    rule_id: str
    recommended_change: str
    regression_case: dict[str, Any]


BUILTIN_RULES: dict[str, RuleMetadata] = {
    "codex-dogfood": RuleMetadata(
        "codex-dogfood",
        "Tracker dogfooding",
        "codex",
        "AGENTS.md",
        critical=True,
        priority=1,
    ),
    "acceptance-criteria": RuleMetadata(
        "acceptance-criteria",
        "Acceptance criteria required",
        "codex",
        "AGENTS.md",
        critical=True,
        priority=2,
    ),
    "dirty-worktree": RuleMetadata("dirty-worktree", "Dirty worktree handling", "codex", "AGENTS.md", critical=True),
    "verification": RuleMetadata("verification", "Verification evidence", "codex", "AGENTS.md", critical=True),
    "closeout-evidence": RuleMetadata("closeout-evidence", "Closeout evidence", "codex", "AGENTS.md", critical=True),
    "safety-boundaries": RuleMetadata("safety-boundaries", "Safety boundaries", "codex", "AGENTS.md", critical=True),
    "schema-migration": RuleMetadata(
        "schema-migration",
        "Schema and migration safety",
        "codex",
        "AGENTS.md",
        risk_categories=("schema", "migration"),
        critical=True,
        priority=10,
    ),
    "auth-secrets": RuleMetadata(
        "auth-secrets",
        "Auth and secret safety",
        "codex",
        "AGENTS.md",
        risk_categories=("auth", "secrets"),
        critical=True,
        priority=10,
    ),
    "deployment-config": RuleMetadata(
        "deployment-config",
        "Deployment and configuration drift",
        "codex",
        "AGENTS.md",
        risk_categories=("deployment",),
        critical=True,
        priority=20,
    ),
    "mcp-contract": RuleMetadata(
        "mcp-contract",
        "MCP contract and token discipline",
        "codex",
        "AGENTS.md",
        risk_categories=("mcp",),
        critical=True,
        priority=20,
    ),
    "ui-provenance": RuleMetadata(
        "ui-provenance",
        "Protected UI provenance",
        "codex",
        "AGENTS.md",
        risk_categories=("ui", "magicpatterns"),
        critical=True,
        priority=20,
    ),
    "backup-safety": RuleMetadata(
        "backup-safety",
        "Backup and artifact safety",
        "codex",
        "AGENTS.md",
        risk_categories=("backup",),
        critical=True,
        priority=15,
    ),
    "guidance-sync-safety": RuleMetadata(
        "guidance-sync-safety",
        "Guidance sync review-first safety",
        "codex",
        "AGENTS.md",
        risk_categories=("guidance-sync",),
        critical=True,
        priority=15,
    ),
    "documentation-durable": RuleMetadata(
        "documentation-durable",
        "Durable documentation",
        "codex",
        "AGENTS.md",
        project_types=("documentation-only",),
        priority=60,
    ),
}


class RuleRelevanceService:
    def __init__(self, repository_root: Path | None = None, rules: list[RuleMetadata] | None = None):
        self.repository_root = repository_root or Path.cwd()
        self.rules = {rule.rule_id: rule for rule in (rules or BUILTIN_RULES.values())}

    def scan_inventory(
        self,
        root: Path | None = None,
        branch: str = "local",
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        root = (root or self.repository_root).resolve()
        surfaces = [
            "AGENTS.md",
            "AGENTS*.md",
            ".codex/rules/*",
            ".cursor/rules/*.mdc",
            ".cursor/skills/**/*",
            "CLAUDE.md",
            "documentation/prompts/**/*.md",
            "documentation/design/**/*.md",
        ]
        files: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()
        missing_metadata: list[str] = []
        for pattern in surfaces:
            for path in root.glob(pattern):
                if not path.is_file() or any(part in {"exports", "backups", ".git"} for part in path.parts):
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                relative = path.relative_to(root).as_posix()
                rule_id = self._extract_rule_id(text) or self._path_rule_id(relative)
                if "rule-id:" not in text.lower() and relative not in {"AGENTS.md", "CLAUDE.md"}:
                    missing_metadata.append(relative)
                if rule_id in seen_ids:
                    duplicate_ids.add(rule_id)
                seen_ids.add(rule_id)
                files.append(
                    {
                        "rule_id": rule_id,
                        "path": relative,
                        "harness": self._harness(relative),
                        "branch": branch,
                        "commit_sha": commit_sha,
                        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        "protected": relative.startswith("documentation/design/"),
                    }
                )
        return {
            "files": sorted(files, key=lambda item: item["path"]),
            "missing_metadata": sorted(missing_metadata),
            "duplicate_rule_ids": sorted(duplicate_ids),
            "unsupported_harnesses": [],
            "stale_mirrors": [],
        }

    def resolve(
        self,
        project_types: list[str],
        harness: str = "codex",
        task_type: str = "implementation",
        changed_paths: list[str] | None = None,
        risk_labels: list[str] | None = None,
        include_optional: bool = False,
    ) -> RuleResolution:
        changed_paths = changed_paths or []
        risk_labels = [label.lower() for label in (risk_labels or [])]
        required_ids = set(CRITICAL_BASELINE)
        explanation = ["critical baseline applied"]
        for project_type in project_types:
            pack = RULE_PACKS.get(project_type, set())
            required_ids.update(pack)
            if pack:
                explanation.append(f"pack {project_type} applied")
        for path in changed_paths:
            if "migrations/" in path or "models.py" in path:
                risk_labels.append("schema")
            if "mcp/" in path:
                risk_labels.append("mcp")
            if "deployment/" in path:
                risk_labels.append("deployment")
            if "documentation/design/" in path or "MagicPatterns" in path:
                risk_labels.append("magicpatterns")
        for risk in set(risk_labels):
            rules = RISK_RULES.get(risk, set())
            required_ids.update(rules)
            if rules:
                explanation.append(f"risk {risk} applied")
        expanded = self._expand_dependencies(required_ids)
        rules: list[EffectiveRule] = []
        missing: list[str] = []
        conflicts: list[str] = []
        for rule_id in expanded:
            rule = self.rules.get(rule_id)
            if rule is None:
                missing.append(rule_id)
                continue
            if rule.harness != harness and rule.harness != "all":
                continue
            if rule.deprecated:
                status = "deprecated"
            elif rule.critical or rule_id in required_ids:
                status = "required"
            else:
                status = "recommended"
            rules.append(EffectiveRule(rule, status, "matched baseline, pack, changed path, or risk"))
            conflicts.extend(
                f"{rule.rule_id} conflicts with {conflict}" for conflict in rule.conflicts if conflict in expanded
            )
        ordered = sorted(rules, key=lambda item: (item.metadata.priority, item.metadata.rule_id))
        blocking_missing = sorted(rule_id for rule_id in missing if self.rules.get(rule_id, None) is None)
        return RuleResolution(
            "blocked" if blocking_missing or conflicts else "ok",
            ordered,
            blocking_missing,
            sorted(conflicts),
            explanation,
        )

    def lint_prompt(
        self,
        prompt_text: str,
        project_types: list[str],
        harness: str = "codex",
        task_type: str = "implementation",
        changed_paths: list[str] | None = None,
        risk_labels: list[str] | None = None,
        expected_model: str = "GPT-5.5",
        expected_reasoning: str = "high",
    ) -> PromptLintResult:
        resolution = self.resolve(project_types, harness, task_type, changed_paths, risk_labels)
        expected_rule_ids = [item.metadata.rule_id for item in resolution.rules if item.metadata.critical]
        missing_rules = [rule_id for rule_id in expected_rule_ids if rule_id not in prompt_text]
        errors: list[str] = []
        warnings: list[str] = []
        if missing_rules:
            errors.append("Prompt is missing critical applicable rule IDs")
        if "- [ ]" not in prompt_text:
            errors.append("Prompt is missing pass/fail acceptance criteria")
        if "pytest" not in prompt_text and "verification" not in prompt_text.lower():
            errors.append("Prompt is missing verification commands")
        if "## STOP" not in prompt_text:
            errors.append("Prompt is missing STOP handoff")
        if expected_model not in prompt_text or expected_reasoning not in prompt_text:
            warnings.append("Prompt model or reasoning guidance does not match expected recommendation")
        status = "block" if errors else "warn" if warnings else "pass"
        return PromptLintResult(
            status,
            missing_rules,
            warnings,
            errors,
            {
                "status": status,
                "missing_critical_rules": missing_rules,
                "warnings": warnings,
                "errors": errors,
                "effective_rule_count": len(resolution.rules),
            },
        )

    def compile_prompt(
        self,
        title: str,
        context: str,
        acceptance_criteria: list[str],
        verification_commands: list[str],
        stop_handoff: str,
        project_types: list[str],
        changed_paths: list[str] | None = None,
        risk_labels: list[str] | None = None,
    ) -> str:
        resolution = self.resolve(project_types, changed_paths=changed_paths, risk_labels=risk_labels)
        rule_lines = "\n".join(f"- `{item.metadata.rule_id}`: {item.metadata.title}" for item in resolution.rules)
        ac_lines = "\n".join(f"- [ ] {item}" for item in acceptance_criteria)
        command_lines = "\n".join(f"- `{command}`" for command in verification_commands)
        return (
            f"# {title}\n\n"
            "Recommended model/reasoning: GPT-5.5 high\n\n"
            f"## Context\n{context}\n\n"
            f"## Effective Rules\n{rule_lines}\n\n"
            f"## Acceptance Criteria\n{ac_lines}\n\n"
            f"## Verification\n{command_lines}\n\n"
            f"## STOP\n{stop_handoff}\n"
        )

    def record_missing_rule_incident(
        self,
        missed_rule: str,
        task_context: dict[str, Any],
        recommended_change: str,
    ) -> MissingRuleIncident:
        rule_id = self._path_rule_id(missed_rule)
        return MissingRuleIncident(
            "recorded",
            rule_id,
            recommended_change,
            {"missed_rule": missed_rule, "task_context": task_context, "expected_status": "block"},
        )

    def remote_branch_inventory(self, repo: str, branches: dict[str, dict[str, str]]) -> dict[str, Any]:
        return {
            "repo": repo,
            "branches": [
                {"name": name, "commit_sha": data.get("commit_sha"), "guidance_paths": sorted(data.get("paths", []))}
                for name, data in sorted(branches.items())
            ],
            "auth_required": False,
        }

    def side_by_side_diff(self, left: str, right: str, path: str) -> dict[str, Any]:
        diff = "\n".join(
            difflib.unified_diff(
                left.splitlines(),
                right.splitlines(),
                fromfile=f"source/{path}",
                tofile=f"target/{path}",
                lineterm="",
            )
        )
        return {"path": path, "status": "different" if left != right else "in-sync", "diff": diff[:12000]}

    def version_manifest(self, rules: list[RuleMetadata] | None = None) -> dict[str, Any]:
        selected = rules or list(self.rules.values())
        return {
            "schema_version": "rule-manifest-v1",
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "version": rule.version,
                    "critical": rule.critical,
                    "dependencies": list(rule.dependencies),
                    "deprecated": rule.deprecated,
                }
                for rule in sorted(selected, key=lambda item: item.rule_id)
            ],
            "upgrade_notes": "Review critical rule changes before syncing child projects.",
        }

    def sync_next_actions(self, project_types: list[str]) -> dict[str, Any]:
        resolution = self.resolve(project_types, risk_labels=["guidance-sync", "backup"])
        return {
            "status": resolution.status,
            "critical_rules": [item.metadata.rule_id for item in resolution.rules if item.metadata.critical],
            "next": "Lint prompts and review sync proposals before opening PRs.",
        }

    def _expand_dependencies(self, rule_ids: set[str]) -> set[str]:
        expanded = set(rule_ids)
        changed = True
        while changed:
            changed = False
            for rule_id in list(expanded):
                rule = self.rules.get(rule_id)
                if not rule:
                    continue
                for dependency in rule.dependencies:
                    if dependency not in expanded:
                        expanded.add(dependency)
                        changed = True
        return expanded

    @staticmethod
    def _extract_rule_id(text: str) -> str | None:
        match = re.search(r"rule-id:\s*([A-Za-z0-9_.-]+)", text, flags=re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _path_rule_id(path: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", Path(path).stem.lower()).strip("-") or "rule"

    @staticmethod
    def _harness(path: str) -> str:
        if path.startswith(".cursor/"):
            return "cursor"
        if path.startswith(".codex/") or path.startswith("AGENTS"):
            return "codex"
        if path == "CLAUDE.md":
            return "claude"
        return "docs"
