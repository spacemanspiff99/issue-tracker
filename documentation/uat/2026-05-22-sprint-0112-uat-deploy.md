# UAT Deploy Notes: Sprint 0112

Date: 2026-05-22
Target: `app-uat` / `192.168.10.26`
Branch: `deploy/app-host-targets-0112`
Deployed SHA: `cf6257727ab908291aba1873c49167f39fc2cdfd`
Successful workflow run: `26271545892`

## Result

Sprint 0112 UAT deployment passed.

The deployed application answered:

```json
{"ok":true,"database":"ok"}
```

## Evidence

Successful workflow run `26271545892` deployed exactly `cf6257727ab908291aba1873c49167f39fc2cdfd` to:

```text
akun@192.168.10.26:/home/akun/issue-tracker/current
```

The workflow recorded a pre-migration backup at:

```text
/home/akun/issue-tracker/backups/cf6257727ab908291aba1873c49167f39fc2cdfd-20260522060939/pre-migration.dump
```

Remote gates passed:

- Full tests: `47 passed, 1 skipped, 1 warning in 12.35s`.
- Ruff: `All checks passed!`.
- UAT `/health`: `{"ok":true,"database":"ok"}`.
- MCP smoke passed and listed project, issue, sprint, category, Guidance Sync, backup, rule, prompt, and sync tools.
- Browser UAT: `1 passed, 1 warning in 26.50s`.

The workflow ended with:

```text
Deployed cf6257727ab908291aba1873c49167f39fc2cdfd to uat at akun@192.168.10.26:/home/akun/issue-tracker/current
```

## Prior Failed Run

Workflow run `26271139679` failed before this successful run while testing SHA `96652c94fd1deaa26f5706dd1e16e6a162635b03`.

Failure evidence:

```text
PermissionError: [Errno 13] Permission denied: 'exports/voice-feedback'
```

Resolution:

- `deployment/scripts/remote-compose-deploy.sh` now creates `exports` and `backups` on the target host before remote tests.
- It applies writable permissions to those runtime artifact directories before running the container test gate.
- The fixed branch was pushed as `deploy/app-host-targets-0112` to avoid force-pushing the already-pushed candidate branch.

## Release Decision

Sprint 0112 is complete for UAT deployment and deployment-gate validation.

Production promotion is not approved by this note. The next required work is Sprint 0119, which runs the comprehensive production-readiness test drill from `documentation/guides/comprehensive-test-plan.md` before any production-project rollout decision.
