# 0178: Production on k3s with a shared PostgreSQL

Status: design, not started. Tracker issue `0178` (Sprint `0168` follow-on).

Recommended model/reasoning: Claude Opus at high effort, or GPT-5.5 `high` (`deep` tier). This work covers deployment, the schema/migration path, secrets, and production data safety.

## Context

- Owner decision (2026-11-05): production runs on k3s and uses a shared PostgreSQL container that other services also use. It does not get its own dedicated Postgres container.
- UAT now runs on the dev host (`192.168.10.20`) as an isolated compose stack, deployed locally by `deployment/scripts/local-uat-deploy.sh`. See `documentation/guides/deployment.md`.
- No GitHub Actions runners are used. The old `.github/workflows/local-pipeline.yml` prod job targets `app-prod` / `192.168.10.27`, which is unreachable from the dev host (`No route to host` on 2026-11-05). That job is superseded by this issue.
- Production data is the durable source of truth. Deploys are forward-only, take a backup before migrating, and never copy, reset, or restore data implicitly. See `AGENTS.md`.

## Open questions (owner)

1. **Cluster:** which k3s cluster, node, and `kubeconfig` context, and which namespace for issue-tracker?
2. **Shared Postgres:** the in-cluster Service DNS name and port, the Postgres major version (local and UAT use 16), and who administers it.
3. **Existing prod data:** does an issue-tracker production database already exist anywhere, for example on `192.168.10.27`? If it does, moving it is a separate migration plan with its own backup and verification.
4. **Image delivery:** how images reach the cluster without CI runners. Options include a local registry, `k3s ctr images import`, or GHCR.
5. **Ingress/TLS:** Traefik (the k3s default) plus cert-manager for `it.462111.xyz`, and where DNS is managed.
6. **Backups:** what already backs up the shared Postgres, and where issue-tracker pre-migration dumps should go.

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

Do not create cluster resources, databases, roles, or Secrets until the owner answers the open questions. Any first production deploy needs the exact SHA, backup plan, and rollback outline stated, followed by explicit owner confirmation.
