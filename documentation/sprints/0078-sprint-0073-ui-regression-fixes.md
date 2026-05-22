# Sprint 0078: Sprint 0073 UI Regression Fixes

Status: complete in the local tracker

Tracker sprint: `0078` Fix Sprint 0073 UI regressions and Playwright gate

Origin: user-reported regressions after Sprint `0073`.

## Problem

Two major regressions need correction before the MagicPatterns UI work should be considered ready:

- Voice intake recording appears inert when clicking the record button.
- Voice intake should support audio-only urgent notes without requiring a title or subject, so the next Codex run can process them into actionable issues.
- The left-hand navigation buttons are too large and the server-rendered adaptation drifted from the protected MagicPatterns AppShell.

The protected source artifact remains `documentation/design/magicpatterns/UI.tsx`. Do not edit it. Implementation changes should happen in FastAPI/Jinja templates, CSS, service code, tests, and documentation only.

## Model And Reasoning

Recommended model/reasoning: GPT-5.5 `medium` for normal UI, route, service, and Playwright test work.

Escalate to GPT-5.5 `high` if browser permission handling, persisted tracker-state processing, auth/session behavior, or destructive tracker recovery becomes difficult.

## Backlog

| Tracker ID | Issue | Category | Priority | Acceptance Summary |
|---|---|---|---|---|
| `0074` | Fix voice intake recording and audio-only urgent processing | `WEB-3` | urgent | Record/stop/attach works; title is optional; audio-only submissions create an urgent `To process: urgent audio note`-style issue discoverable by future Codex runs. |
| `0075` | Restore MagicPatterns sidebar sizing and protected UI fidelity | `WEB-1` | high | Left nav sizing and active state match the MagicPatterns AppShell intent; protected source artifact remains unchanged. |
| `0076` | Audit protected MagicPatterns source and implementation boundaries | `WEB-4` | high | Verify `documentation/design/magicpatterns/UI.tsx` has not been modified and document allowed implementation files. |
| `0077` | Add comprehensive Playwright UI regression gate for corrective UI sprint | `WEB-4` | high | Playwright covers desktop/mobile UI, browser MediaRecorder behavior with a fake microphone device, screenshots, no horizontal overflow, and dated UAT evidence. |

## Dependency-Aware Execution Plan

1. Complete `0076` first. Confirm the protected MagicPatterns source artifact is unchanged, list allowed implementation files, and record the audit evidence before any UI edits.
2. Complete `0074` next. Debug from browser evidence, then fix voice intake so Record visibly starts or shows a real error, Stop attaches audio, and audio-only urgent notes are created without title/subject.
3. Complete `0075` after re-reading the MagicPatterns `AppShell` source. Adjust only the server-rendered adaptation so the left navigation is not oversized and remains visually faithful.
4. Complete `0077` last. Build the Playwright gate around the fixed behavior and run it through Docker with desktop/mobile screenshots and a dated UAT note.

## Playwright Test Plan

The Playwright gate should cover:

- setup/login or existing admin login
- project overview shell, left navigation, and top bar at desktop and mobile sizes
- backlog, board, releases, categories, sprints, planning, and backup routes
- issue detail page and sidebar/drawer-equivalent metadata
- voice intake record button, stop button, preview/attachment state, upload fallback, and audio-only urgent submission
- microphone behavior using browser permissions and Chromium fake media stream flags
- no horizontal overflow on key desktop/mobile pages
- screenshots under ignored local artifacts and a dated UAT note under `documentation/uat/`

Recommended command shape:

```bash
docker compose -f deployment/docker-compose.local.yml up -d --build
docker compose -f deployment/docker-compose.local.yml exec app python -m pytest tests/e2e/test_browser_uat.py
```

If the existing opt-in `RUN_BROWSER_UAT=1` guard remains, the sprint must document and run the exact command that enables it.

## Verification Commands

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_web_routes.py
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
```

Plus the Playwright command from the final implementation.

## Close Evidence

Protected source audit:

- `git diff -- documentation/design/magicpatterns/UI.tsx` produced no output.
- Implementation changes were limited to service, web route/template/CSS, test, and UAT documentation surfaces. The protected MagicPatterns source artifact was not edited.

Commands run on 2026-05-15:

```bash
docker compose -f deployment/docker-compose.local.yml up -d --build app
curl -fsS http://127.0.0.1:8000/health
docker compose -f deployment/docker-compose.local.yml exec app python -m pytest tests/unit/test_services.py tests/integration/test_web_routes.py
docker compose -f deployment/docker-compose.local.yml exec app python -m ruff check --no-cache .
docker compose -f deployment/docker-compose.local.yml exec app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/test_browser_uat.py
docker compose -f deployment/docker-compose.local.yml exec app issue-tracker generate-dev-certs --force --host 192.168.10.20
docker compose -f deployment/docker-compose.local.yml --profile https up -d app-https
curl -k -fsS https://127.0.0.1:8443/health
docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 -e UAT_BASE_URL=https://127.0.0.1:8443 -e UAT_IGNORE_HTTPS_ERRORS=1 app-https python -m pytest tests/e2e/test_browser_uat.py
```

Results:

- `/health`: `{"ok":true,"database":"ok"}`.
- Unit + web route focused gate: 20 passed.
- Ruff: all checks passed.
- Full test suite: 27 passed, 1 skipped. The skipped test is the opt-in browser UAT guard when `RUN_BROWSER_UAT=1` is not set.
- Explicit Playwright gate: 1 passed with Chromium fake microphone using the real `MediaRecorder` API, non-empty recorded audio attachment, immediate requesting-microphone feedback, audio-only urgent intake creation, desktop/mobile screenshots, compact sidebar height assertions, and post-test archival of the temporary UAT project.
- LAN HTTPS browser path: passed without a tunnel using generated local CA/server certificates and the `app-https` compose profile on port `8443`.
- Tunnel cleanup: the removed Cloudflare tunnel compose service was not retained, and the old orphan tunnel container was removed with `--remove-orphans`.
- Direct browser recording diagnostic: status reached `Recording attached. Submit the intake form to save it.` and the attached WebM file was non-empty.
- Sidebar browser measurement after correction: nav rows render at about 38px tall instead of the prior stretched ~214px rows.
- Local project cleanup: generated Browser UAT projects and `Manual-UAT-Restored` were archived non-destructively; only the canonical `issue-tracker` project remains active by default.
- Known warning: pytest could not write `.pytest_cache` inside the Docker-mounted app directory; this did not affect verification.

UAT note: `documentation/uat/2026-05-15-sprint-0078-browser-uat.md`

Ignored local screenshot artifacts:

- `exports/browser-uat-0078/desktop-project-empty.png`
- `exports/browser-uat-0078/desktop-issue-detail.png`
- `exports/browser-uat-0078/desktop-sprint-detail.png`
- `exports/browser-uat-0078/desktop-board.png`
- `exports/browser-uat-0078/desktop-releases.png`
- `exports/browser-uat-0078/desktop-intake.png`
- `exports/browser-uat-0078/mobile-project-detail.png`
- `exports/browser-uat-0078/mobile-issue-detail.png`
- `exports/browser-uat-0078/mobile-board.png`
- `exports/browser-uat-0078/mobile-backup.png`
- `exports/browser-uat-0078/mobile-intake.png`

## STOP

Sprint `0078` is complete and closed with route, service, and Playwright evidence.
