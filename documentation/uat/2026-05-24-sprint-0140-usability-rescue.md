# Local UAT Notes: Sprint 0140 Usability Rescue Browser UAT

Date: 2026-05-24
Tester: Codex Playwright in Docker
Browser: Playwright Chromium inside the Docker app container
Environment: Docker Compose local app and PostgreSQL

## Result

Browser UAT passed for desktop and mobile viewports.

Setup/login note: First-run setup created the UAT admin user.

## Evidence

Command:

```bash
docker compose -f deployment/docker-compose.local.yml exec app python -m pytest tests/e2e/test_browser_uat.py
```

HTTPS/local-CA verification command:

```bash
docker compose -f deployment/docker-compose.local.yml exec   -e RUN_BROWSER_UAT=1   -e UAT_BASE_URL=https://127.0.0.1:8443   -e UAT_IGNORE_HTTPS_ERRORS=1   app-https python -m pytest tests/e2e/test_browser_uat.py
```

Screenshots were generated under ignored local path `exports/browser-uat-0140/`.

## Covered Paths

- setup or existing-setup login
- project search and project creation
- recommended taxonomy
- issue validation, quick create, issue detail, dependency creation, and close metadata
- sprint creation, assignment, and progress summary
- overview drill-down links, saved backlog views, sprint-filtered board navigation, release count drill-downs
- Guidance Sync, intake, and backup guidance
- tooltip affordance visibility on primary project surfaces
- browser MediaRecorder record/stop/preview attachment using Chromium's fake microphone device
- secure-context voice intake over HTTPS/local CA
- audio-only urgent intake creation
- desktop viewport usability
- mobile viewport usability
