# Issue 0013: Add Stable Loki Labels For Container Logs

Status: backlog
Recommended model: GPT-5.5 high
Category gates: `IT-5`, `IT-6`

## Problem

Live Loki verification on 2026-05-24 showed host-level journald streams for UAT and production hosts, but did not show issue-tracker container streams with stable `environment`, `app`, `service`, or `container` labels. Dev was not present in Loki labels, and UAT app/Postgres logs could not be distinguished from other containers on the same host.

## Scope

- Application-side logging standard:
  - Web and MCP processes emit structured stderr logs with stable `app`, `service`, `source`, and `environment` fields.
  - Web request logs use route templates rather than raw paths, and do not include query strings, request bodies, cookies, or session values.
  - Uvicorn access logs stay disabled in container startup so Docker log shipping uses the sanitized application request summaries.
- Add or update the host-level log collector configuration for dev, UAT, and production.
- Ship Docker container stdout/stderr logs for the issue-tracker `app` and `postgres` containers.
- Apply stable labels:
  - `environment`: `dev`, `uat`, or `production`
  - `app`: `issue-tracker`
  - `service`: `app` or `postgres`
  - `container`: stable container name
  - `host`: VM or host name
  - `source`: `docker`, `container`, `journald`, or `app-log`
- Avoid labels that expose secrets, local paths, tokens, dynamic container IDs, image hashes, compose config hashes, or other high-cardinality values.
- Keep this change separate from deployment or data-refresh work.

## Acceptance Criteria

- [ ] Loki `/labels` includes the stable label keys needed by dashboards.
- [ ] Loki `/label/environment/values` returns `dev`, `uat`, and `production`.
- [ ] Loki `/series` proves streams exist for each expected issue-tracker container in dev, UAT, and production.
- [ ] Queries can distinguish dev, UAT, and production without relying on hostnames alone.
- [ ] No sensitive or high-cardinality labels are introduced.

## Category Checklists

`IT-5` Auth And Secret Safety: Verify password hashing, session flags, setup flow, secret handling, and no credential logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
ssh ubuntu@192.168.10.32
curl -fsS http://192.168.10.47/loki/api/v1/labels
curl -fsS http://192.168.10.47/loki/api/v1/label/environment/values
curl -fsG --data-urlencode 'match[]={app="issue-tracker"}' http://192.168.10.47/loki/api/v1/series
curl -fsG --data-urlencode 'query={app="issue-tracker",environment="uat"}' --data-urlencode 'limit=20' http://192.168.10.47/loki/api/v1/query_range
```

## STOP

Stop when live Loki queries from the monitoring host prove every expected issue-tracker container logs with stable environment, app, service, container, host, and source labels.
