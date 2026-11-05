# 0178: Production on k3s with a shared PostgreSQL

Status: blocked on infra (shared Postgres, B2 backups, vault, ingress) by `infra2.dev`. Tracker issue `0178` (Sprint `0168` follow-on).

Recommended model/reasoning: Claude Opus at high effort, or GPT-5.5 `high` (`deep` tier). This work covers deployment, the schema/migration path, secrets, and production data safety.

## Context

- Owner decision (2026-11-05): production runs on k3s and uses a shared PostgreSQL container that other services also use. It does not get its own dedicated Postgres container.
- UAT now runs on the dev host (`192.168.10.20`) as an isolated compose stack, deployed locally by `deployment/scripts/local-uat-deploy.sh`. See `documentation/guides/deployment.md`.
- No GitHub Actions runners are used. The old `.github/workflows/local-pipeline.yml` prod job targets `app-prod` / `192.168.10.27`, which is unreachable from the dev host (`No route to host` on 2026-11-05). That job is superseded by this issue.
- Production data is the durable source of truth. Deploys are forward-only, take a backup before migrating, and never copy, reset, or restore data implicitly. See `AGENTS.md`.

## Owner answers (2026-11-05)

1. **Shared Postgres does not exist yet.** A generic Postgres for k3s prod must be built first, with local and remote backups to Backblaze B2.
2. **Secrets:** a generic vault on k3s is required.
3. **Existing prod data:** none ("just Linear"). A read-only check of `app-uat` (`192.168.10.26`) on 2026-11-05 found no issue-tracker data, files, or volumes; its backups are weather-app dumps. There is nothing to migrate.
4. **Image delivery / CI:** a k3s runner will be set up when the k3s work is ready.
5. **Ingress/TLS:** owner asked for a recommendation (below).
6. **Ownership:** the infra session `infra2.dev - issue tracker support` builds the shared Postgres, backups, vault, and ingress on k3s prod. This repo owns only the issue-tracker app manifests that consume them. The brief was sent on 2026-11-05.

## Recommendations (sent to infra)

- **Postgres:** CloudNativePG operator with a PG 16 `Cluster`. Each app gets its own database and login role (no superuser, `CREATEDB`, or `CREATEROLE`), and `CONNECT` is revoked from `PUBLIC`.
- **Backups:** CNPG barman-cloud WAL archiving plus scheduled base backups to B2 over its S3-compatible API, giving off-site point-in-time recovery. A separate local copy (volume snapshot or `pg_dump` CronJob to another disk) covers the local side. A test restore is required as evidence.
- **Vault:** OpenBao or HashiCorp Vault with the External Secrets Operator, Kubernetes auth scoped per namespace, unseal and recovery keys held outside the cluster, and Vault storage backed up to B2.
- **Ingress/TLS:** k3s's bundled Traefik plus cert-manager, with a Let's Encrypt DNS-01 wildcard `*.it.462111.xyz`. DNS-01 works for LAN-only hosts without opening port 80. Names: `it.462111.xyz` for prod (k3s), `uat.it.462111.xyz` for UAT (`192.168.10.20:8100`), `dev.it.462111.xyz` for dev (`192.168.10.20:8000`). The DNS host for `462111.xyz` and the split-DNS approach are pending from infra.

## Waiting on infra

- Postgres Service DNS name and port, the `issue_tracker` database and role, and the connection budget.
- Vault/ESO secret path (proposed `apps/issue-tracker/prod`: `DATABASE_URL`, `APP_SECRET_KEY`, `ADMIN_INITIAL_PASSWORD`) and the k8s auth role.
- B2 bucket and prefix layout, backup schedule, and restore evidence.
- Cluster context, namespace, ingress class, and cert issuer.

## Proposed design (to confirm)

- **Isolation inside the shared server:** issue-tracker gets its own database `issue_tracker` and its own login role `issue_tracker`, with no superuser, `CREATEDB`, or `CREATEROLE`. The role owns only that database. Other services' databases stay out of reach: revoke `CONNECT` from `PUBLIC` on `issue_tracker`.
- **Secrets:** a Kubernetes `Secret` holds `DATABASE_URL` and `APP_SECRET_KEY`. Nothing goes into git and no `.env` files are copied.
- **Migrations:** each release runs a Kubernetes `Job` (`alembic upgrade head`, forward-only) before the Deployment rollout, and a failed Job blocks the rollout. Do not run migrations in an initContainer on every replica.
- **Pre-migration backup:** a `pg_dump -Fc -d issue_tracker` of this database only, never `pg_dumpall` of the shared server. The dump must exist and be non-empty before the migration Job runs.
- **App:** a `Deployment` with readiness and liveness probes on `/health`, which checks database connectivity. `SESSION_COOKIE_SECURE=true`, `APP_ENVIRONMENT=production`, and `APP_BASE_URL=https://it.462111.xyz`.
- **Connection budget:** the shared server's `max_connections` is split across services. Set SQLAlchemy pool limits explicitly.
- **MCP:** the stdio MCP server stays local against dev. Exposing prod over MCP is out of scope.

## Acceptance criteria

- [ ] The open questions above are answered and recorded here.
- [ ] Manifests (or a Helm/Kustomize layout) live under `deployment/k8s/` with no secrets committed.
- [ ] A deploy script takes an exact pushed SHA, builds the image from `git archive <sha>`, and refuses unpushed or short SHAs. This matches the guards in `local-uat-deploy.sh`.
- [ ] A dedicated database and role exist, and a test shows the issue-tracker role cannot connect to another service's database.
- [ ] The pre-migration `pg_dump` of `issue_tracker` is taken and verified before the migration Job runs. A failed backup aborts the deploy.
- [ ] The migration Job runs `alembic upgrade head` only. Nothing in the path can run a downgrade, reset, or restore.
- [ ] After rollout, `/health` at `https://it.462111.xyz/health` shows database ok, and the deployed SHA is recorded.
- [ ] The old compose prod job in `.github/workflows/local-pipeline.yml` is removed or explicitly retired.
- [ ] `IT-3` (schema/migration safety), `IT-5` (secret safety), and `IT-6` (deployment/config drift) checklists pass.

## Verification

```bash
kubectl --context <ctx> -n <ns> get deploy,job,svc,ingress
kubectl --context <ctx> -n <ns> logs job/issue-tracker-migrate-<sha>
curl -fsS https://it.462111.xyz/health
```

## STOP

Issue-tracker does not create cluster resources, databases, roles, or Secrets itself; infra owns those. App manifests start once infra returns the items under "Waiting on infra". Any first production deploy needs the exact SHA, backup plan, and rollback outline stated, followed by explicit owner confirmation.
