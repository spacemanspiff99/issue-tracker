from __future__ import annotations

from issue_tracker.services.rule_relevance import RuleMetadata, RuleRelevanceService


def test_rule_inventory_scans_guidance_surfaces_and_flags_missing_metadata(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
    (tmp_path / ".cursor" / "rules").mkdir(parents=True)
    (tmp_path / ".cursor" / "rules" / "ui.mdc").write_text("rule-id: ui-rule\n", encoding="utf-8")
    (tmp_path / ".codex" / "rules").mkdir(parents=True)
    (tmp_path / ".codex" / "rules" / "deploy.rules").write_text("No front matter\n", encoding="utf-8")

    inventory = RuleRelevanceService(tmp_path).scan_inventory()

    paths = [item["path"] for item in inventory["files"]]
    assert "AGENTS.md" in paths
    assert ".cursor/rules/ui.mdc" in paths
    assert ".codex/rules/deploy.rules" in inventory["missing_metadata"]


def test_resolver_applies_packs_risks_dependencies_and_conflicts():
    service = RuleRelevanceService(
        rules=[
            RuleMetadata("codex-dogfood", "Dogfood", "codex", "AGENTS.md", critical=True, priority=1),
            RuleMetadata("acceptance-criteria", "AC", "codex", "AGENTS.md", critical=True, priority=2),
            RuleMetadata("dirty-worktree", "Dirty", "codex", "AGENTS.md", critical=True, priority=3),
            RuleMetadata("verification", "Verify", "codex", "AGENTS.md", critical=True, priority=4),
            RuleMetadata("closeout-evidence", "Close", "codex", "AGENTS.md", critical=True, priority=5),
            RuleMetadata("safety-boundaries", "Safety", "codex", "AGENTS.md", critical=True, priority=6),
            RuleMetadata(
                "schema-migration",
                "Schema",
                "codex",
                "AGENTS.md",
                critical=True,
                dependencies=("deployment-config",),
                priority=10,
            ),
            RuleMetadata("deployment-config", "Deploy", "codex", "AGENTS.md", critical=True, priority=11),
            RuleMetadata(
                "ui-provenance",
                "UI",
                "codex",
                "AGENTS.md",
                critical=True,
                conflicts=("deprecated-ui",),
                priority=12,
            ),
            RuleMetadata("deprecated-ui", "Old UI", "codex", "old.md", priority=99),
        ]
    )

    result = service.resolve(
        ["fastapi-jinja-postgres"],
        changed_paths=["migrations/versions/0004.py", "documentation/design/magicpatterns/view.md"],
        risk_labels=["ui"],
    )

    rule_ids = [item.metadata.rule_id for item in result.rules]
    assert "schema-migration" in rule_ids
    assert "deployment-config" in rule_ids
    assert "ui-provenance" in rule_ids
    assert result.status == "ok"


def test_prompt_linter_blocks_missing_critical_rules_and_stop_handoff():
    result = RuleRelevanceService().lint_prompt(
        "# Prompt\n\nRecommended model/reasoning: GPT-5.5 high\n\n## Acceptance Criteria\n- [ ] done\n",
        ["fastapi-jinja-postgres"],
        changed_paths=["src/issue_tracker/domain/models.py"],
        risk_labels=["schema"],
    )

    assert result.status == "block"
    assert "schema-migration" in result.missing_critical_rules
    assert any("STOP" in error for error in result.errors)


def test_prompt_compiler_includes_rules_acceptance_verification_and_stop():
    prompt = RuleRelevanceService().compile_prompt(
        "Execute issue",
        "Context",
        ["implemented", "verified"],
        ["python -m pytest tests/unit/test_rule_relevance.py"],
        "Close with evidence or name blockers.",
        ["fastapi-jinja-postgres"],
        changed_paths=["src/issue_tracker/mcp/tools.py"],
        risk_labels=["mcp"],
    )

    lint = RuleRelevanceService().lint_prompt(
        prompt,
        ["fastapi-jinja-postgres"],
        changed_paths=["src/issue_tracker/mcp/tools.py"],
        risk_labels=["mcp"],
    )
    assert "`mcp-contract`" in prompt
    assert "## STOP" in prompt
    assert lint.status == "pass"


def test_rule_diff_manifest_incident_and_remote_inventory_are_compact():
    service = RuleRelevanceService()
    diff = service.side_by_side_diff("a\n", "b\n", "AGENTS.md")
    manifest = service.version_manifest()
    incident = service.record_missing_rule_incident("backup safety", {"risk": "backup"}, "Mark backup safety critical")
    inventory = service.remote_branch_inventory("owner/repo", {"main": {"commit_sha": "abc", "paths": ["AGENTS.md"]}})

    assert diff["status"] == "different"
    assert manifest["schema_version"] == "rule-manifest-v1"
    assert incident.status == "recorded"
    assert inventory["branches"][0]["name"] == "main"
