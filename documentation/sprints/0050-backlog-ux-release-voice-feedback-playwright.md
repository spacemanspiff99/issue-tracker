# Sprint 0050: Backlog UX, Release Planning, Voice Feedback, And Playwright Gate

Status: complete
Tracker goal: Complete backlog UX, release planning, voice feedback, and Playwright quality gate
Recommended model: GPT-5.5 high for schema, release planning, voice/audio privacy, and browser/runtime debugging; GPT-5.5 medium for bounded route/template work after the design is proven.

## Backlog Review

Open backlog at sprint creation:

| Issue | Title | Phase |
|---|---|---|
| `0051` | Research PM tool UX patterns and define AI-coding tracker design principles | ux-research |
| `0052` | Clean up project model and prevent UAT/import project clutter | project-hygiene |
| `0053` | Add top-level tabs and workspace navigation shell | navigation-redesign |
| `0054` | Design AI/manual workflow states for Codex-ready issue handoff | ai-workflows |
| `0046` | Add release planning across multiple sprints | release-foundation |
| `0055` | Make board sprint-based with single and multi-sprint filters | board-sprint-filtering |
| `0044` | Add easy issue-to-sprint assignment from issue page and drag/drop views | issue-navigation |
| `0045` | Polish drag-and-drop issue ordering across backlog and board | issue-navigation |
| `0047` | Add issue sidebar for fast issue visibility and navigation | issue-navigation |
| `0048` | Add voice feedback intake for audio bug reports and feature requests | voice-feedback |
| `0049` | Add comprehensive containerized Playwright regression suite | playwright-gate |

## Scope

UX research and product principles are recorded in
`documentation/guides/ai-coding-tracker-ux.md`.
The current product purpose and functionality are documented in
`documentation/guides/product-guide.md`.

This sprint should complete the full current backlog, not just a slice.

1. Release planning foundation:
   Implement release-level planning for meta milestones such as MVP release and v1.0. Decide whether this needs schema support or can be service-managed metadata. Release detail must roll up issues, sprints, blockers, progress, and readiness notes.

2. Product UX foundation:
   Research Linear, ClickUp, Trello, GitHub Projects, and similar tools. Borrow useful patterns such as saved views, tabs, sidebars, boards, release/initiative planning, dashboards, and triage while keeping the product focused on steering AI coding work rather than becoming a generic PM suite.

3. Project hygiene and navigation:
   Clean up confusing project list behavior, explain or hide UAT/import project clutter, and add top-level tabs for core workspace areas.

4. AI/manual workflow model:
   Make the product reflect how work enters the tracker: rough human input, Codex investigation, clarification, ready-for-build issue shaping, implementation, verification, and closeout.

5. Issue navigation, sprint board, and assignment ergonomics:
   Add easy issue-to-sprint assignment from issue detail and list contexts, make the board sprint-based with top filters for one or multiple sprints, polish backlog/board drag-and-drop with accessible fallbacks, and add a responsive issue sidebar for fast navigation.

6. Voice feedback intake:
   Add a safe audio feedback intake path for bug reports and feature requests. Do not hardcode external STT or LLM providers. The app should create intake records that Codex can process into investigated, build-ready backlog issues. Ambiguous intake belongs in `CLARIFY` until questions are resolved.

7. Comprehensive Playwright gate:
   Expand the containerized Playwright suite to cover all current critical flows plus the new features. Browser tooling must run inside Docker only.

## Acceptance Criteria

- [x] All assigned issues `0044` through `0049` and `0051` through `0055` are closed with evidence.
- [x] PM tool research is converted into AI-coding-specific design principles and linked from the sprint.
- [x] Project list clutter is resolved without destructive data loss.
- [x] Top-level tabs make workspace navigation obvious and mobile-safe.
- [x] AI/manual workflow states make intake, clarification, ready-for-Codex, implementation, verification, and closeout clear.
- [x] Release planning works across multiple sprints and shows useful rollups.
- [x] Board defaults to sprint-oriented views and supports single-sprint plus multi-sprint filters.
- [x] Issue-to-sprint assignment is available from issue detail and list/sidebar workflows.
- [x] Drag-and-drop backlog/board workflows have route-tested service invariants and browser-tested UI behavior.
- [x] Issue sidebar is useful on desktop and does not overlap content on mobile.
- [x] Voice feedback intake stores audio safely, creates an intake record, and supports a Codex processing handoff into backlog issues.
- [x] Ambiguous voice feedback can be marked `Not Done / Needs Clarifications`.
- [x] Playwright tests run only inside Docker and cover desktop and mobile viewports.
- [x] UAT notes and screenshots are recorded under `documentation/uat/` and ignored local artifact folders.
- [x] No raw audio, screenshots, exports, backups, credentials, or generated local artifacts are committed.

## Completion Evidence

Completed on 2026-05-15 by Codex using GPT-5.5 high reasoning. The active runtime database records Sprint `0050` as closed and closes issues `0044` through `0049` plus `0051` through `0055`.

Implemented surfaces:

- Release planning view backed by issue milestone/readiness metadata.
- AI workflow and voice intake view with ignored local audio artifact storage.
- Sprint-filtered board with single and multi-sprint filters plus route-backed assignment and ordering fallbacks.
- Responsive issue sidebar with workflow, sprint assignment, dependency, metadata, reference, and closeout controls.
- Non-destructive project archive/restore flow for UAT/import clutter.
- AI-coding tracker UX principles in `documentation/guides/ai-coding-tracker-ux.md`.

Verification passed:

```bash
python3 -m compileall src tests
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://localhost:8000/health
docker compose -f deployment/docker-compose.local.yml exec -u root app env RUN_BROWSER_UAT=1 python -m pytest tests/e2e/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
git diff --check
LC_ALL=C grep -RIn '[^ -~]' README.md AGENTS.md .cursor/rules documentation src tests migrations deployment .env.example pyproject.toml alembic.ini
```

Local host note: `python -m pytest tests/` was blocked because `python` is not installed on the host PATH; Docker verification passed with the project-defined Python environment.

## Verification Gate

Run the final gate before closing the sprint:

```bash
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://localhost:8000/health
docker compose -f deployment/docker-compose.local.yml exec -u root app env RUN_BROWSER_UAT=1 python -m pytest tests/e2e/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
git diff --check
LC_ALL=C grep -RIn '[^ -~]' README.md AGENTS.md .cursor/rules documentation src tests migrations deployment .env.example pyproject.toml alembic.ini
```

If schema changes are introduced, verify empty-database upgrade evidence before closing release-planning work.

## STOP

Stop only when Sprint 0050 is complete and closed, or when a named blocker prevents further progress.

If blocked, record:

- exact command or browser step that failed
- owner action required
- next smallest retry command
- tracker issue affected
- whether any issue should remain `CLARIFY`
