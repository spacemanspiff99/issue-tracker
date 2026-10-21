#!/usr/bin/env bash
# Deploy one overlay to the cluster in the current kubectl context, in the only safe order:
#   long-lived resources (except the app) -> Postgres ready -> pre-deploy backup Job
#   -> migration Job (refuses without that exact backup) -> app rollout -> /health "database": "ok".
# There is deliberately no flag to skip the backup or to run a downgrade.
#
# Usage: deployment/k8s/deploy.sh <uat|prod> <image@sha256:digest | image:tag> <git-sha>
# The kubectl context must be named issue-tracker-<uat|prod> (override with EXPECTED_CONTEXT,
# used only by the disposable kind test).
set -euo pipefail

env_name="${1:?usage: deploy.sh <uat|prod> <image-ref> <git-sha>}"
image="${2:?image ref required}"
sha="${3:?git sha required}"
timeout="${DEPLOY_TIMEOUT_SECONDS:-300}"

case "$env_name" in
  uat) ns=issue-tracker-uat ;;
  prod) ns=issue-tracker ;;
  *) echo "unknown environment: $env_name" >&2; exit 2 ;;
esac
[[ "$sha" =~ ^[0-9a-f]{7,40}$ ]] || { echo "not a git sha: $sha" >&2; exit 2; }
if [[ "$image" == *@sha256:* ]]; then
  [[ "$image" =~ @sha256:[0-9a-f]{64}$ ]] || { echo "malformed digest: $image" >&2; exit 2; }
  image_name="${image%@*}" image_pin="digest: ${image#*@}"
elif [[ "${image##*/}" == *:* ]]; then
  image_name="${image%:*}" image_pin="newTag: ${image##*:}"
else
  echo "image needs a digest or an explicit tag: $image" >&2; exit 2
fi

here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d "$here/.render.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

# Render <overlay>/<sub> with the image pinned; output YAML on stdout.
render() {
  local sub="$1" rel="../../overlays/$env_name"
  [ -n "$sub" ] && rel="$rel/$sub"
  mkdir -p "$tmp/r$sub"
  cat > "$tmp/r$sub/kustomization.yaml" <<YAML
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - $rel
images:
  - name: ghcr.io/spacemanspiff99/issue-tracker
    newName: $image_name
    $image_pin
YAML
  kubectl kustomize "$tmp/r$sub"
}

# The backup Job writes exactly this file and the migrate Job's init container checks exactly it.
backup_file="/backups/pre-migration/${sha}-$(date -u +%Y%m%dT%H%M%SZ).dump"
render "" > "$tmp/app.yaml"
render jobs | kubectl set env --local -f - "BACKUP_FILE=$backup_file" -o yaml > "$tmp/jobs.yaml"

# RENDER_ONLY_DIR=<dir>: write the exact manifests this deploy would apply, touch no cluster.
if [ -n "${RENDER_ONLY_DIR:-}" ]; then
  mkdir -p "$RENDER_ONLY_DIR"
  cp "$tmp/app.yaml" "$tmp/jobs.yaml" "$RENDER_ONLY_DIR/"
  echo "rendered $env_name to $RENDER_ONLY_DIR (backup file $backup_file)"
  exit 0
fi

expected_context="${EXPECTED_CONTEXT:-issue-tracker-$env_name}"
context="$(kubectl config current-context)"
if [ "$context" != "$expected_context" ]; then
  echo "refusing: kubectl context is '$context', expected '$expected_context'" >&2
  exit 2
fi

echo "context: $context namespace: $ns image: $image sha: $sha"

wait_job() {
  local job="$1" deadline=$((SECONDS + timeout)) ok failed
  while (( SECONDS < deadline )); do
    ok="$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.succeeded}')"
    failed="$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.failed}')"
    if [ "${ok:-0}" -ge 1 ]; then
      kubectl -n "$ns" logs "job/$job" --all-containers || true
      echo "job $job complete"
      return 0
    fi
    if [ "${failed:-0}" -ge 1 ]; then break; fi
    sleep 3
  done
  echo "job $job did not complete" >&2
  kubectl -n "$ns" describe job "$job" >&2 || true
  kubectl -n "$ns" logs "job/$job" --all-containers >&2 || true
  return 1
}

# Preflight: the owner creates the namespace and Secrets; this script never does. Reading the
# Secrets also proves this credential can act in $ns (it has no cluster-scope rights).
kubectl -n "$ns" get secret issue-tracker-db issue-tracker-app > /dev/null
kubectl -n "$ns" get secret ghcr-pull > /dev/null 2>&1 || echo "warning: secret ghcr-pull missing in $ns; private GHCR pulls will fail" >&2

# Never start while a previous backup, migration or restore is still running.
# Any kubectl error here stops the deploy (set -e); only a missing Job reads as "not active".
for job in issue-tracker-backup-predeploy issue-tracker-migrate; do
  active="$(kubectl -n "$ns" get job "$job" --ignore-not-found -o jsonpath='{.status.active}')"
  if [ "${active:-0}" -ge 1 ]; then
    echo "refusing: job $job is still active in $ns; inspect it before deploying again" >&2
    exit 1
  fi
done
restoring="$(kubectl -n "$ns" get jobs -l app.kubernetes.io/component=restore -o jsonpath='{range .items[?(@.status.active)]}{.metadata.name} {end}')"
if [ -n "$restoring" ]; then
  echo "refusing: restore Job(s) still active in $ns: $restoring" >&2
  exit 1
fi

# 1. Everything except the app Deployment/Service/Ingress (ConfigMap, Postgres, PVCs, CronJob).
kubectl -n "$ns" apply -f "$tmp/app.yaml" -l 'app.kubernetes.io/component!=web'
kubectl -n "$ns" rollout status statefulset/issue-tracker-postgres --timeout="${timeout}s"

# Wait until no app (component=web) pod exists; fail after $1 seconds. Unlike
# `kubectl wait --for=delete -l`, an already-empty selector counts as success. Fails closed:
# if the pod list can't be read, that is an error, never "gone".
wait_app_gone() {
  local deadline=$((SECONDS + $1)) pods
  while :; do
    if ! pods="$(kubectl -n "$ns" get pods -l app.kubernetes.io/component=web -o name --request-timeout=10s)"; then
      echo "could not list app pods in $ns; refusing to assume the app is stopped" >&2
      return 1
    fi
    [ -n "$pods" ] || return 0
    (( SECONDS < deadline )) || { echo "app pod still present after $1s: $pods" >&2; return 1; }
    sleep 2
  done
}

# alembic_version as one line ("" before the first migration). Non-zero exit on any error,
# including when another session holds a lock on alembic_version (fail closed: unknown).
db_version() {
  kubectl -n "$ns" exec -i issue-tracker-postgres-0 -c postgres -- \
    sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -' <<'SQL'
SET lock_timeout = '10s';
SET statement_timeout = '20s';
SELECT to_regclass('public.alembic_version') IS NOT NULL AS has_version \gset
\if :has_version
SELECT string_agg(version_num, ',') FROM alembic_version;
\endif
SQL
}
# On a fresh volume the image's entrypoint first runs a temporary, socket-only server (before
# CREATE DATABASE), so pod readiness alone is not enough: wait for the real server over TCP.
db_deadline=$((SECONDS + timeout))
until kubectl -n "$ns" exec issue-tracker-postgres-0 -c postgres -- \
    sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -X -q -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select 1"' > /dev/null 2>&1; do
  if (( SECONDS >= db_deadline )); then
    echo "Postgres did not accept TCP connections to its database within ${timeout}s" >&2
    kubectl -n "$ns" logs issue-tracker-postgres-0 -c postgres --tail=30 >&2 || true
    exit 1
  fi
  sleep 2
done
echo "postgres: accepting connections"
version_before="$(db_version)"
echo "alembic_version before deploy: ${version_before:-(none)}"

# Maintenance window: stop the app before the backup so no write lands after the dump, and so
# the old code never runs against the migrated schema. On failure before rollout, on_failure
# first deletes the backup/migrate Jobs (foreground, so their pods are gone and an uncommitted
# migration can never COMMIT), then brings the old app back only if alembic_version is
# provably unchanged. Otherwise the app stays at 0 and it says what to check.
phase=""
# Both reads fail the deploy on any API error; only a missing Deployment reads as "".
app_exists="$(kubectl -n "$ns" get deployment issue-tracker --ignore-not-found -o name)"
old_replicas="$(kubectl -n "$ns" get deployment issue-tracker --ignore-not-found -o jsonpath='{.spec.replicas}')"
on_failure() {
  local rc=$? left now jobs_ok=1 version_ok=1
  trap - EXIT INT TERM
  set +e
  [ "$rc" -ne 0 ] || rc=1
  echo "deploy failed during: ${phase:-preflight}" >&2
  kubectl -n "$ns" delete job issue-tracker-backup-predeploy issue-tracker-migrate \
    --ignore-not-found --cascade=foreground --wait=true --timeout=180s >&2
  # Each check below fails closed: an error reading Jobs or the version keeps the app at 0.
  left="$(kubectl -n "$ns" get job issue-tracker-backup-predeploy issue-tracker-migrate --ignore-not-found -o name 2>&1)" || jobs_ok=0
  now="$(db_version 2>&1)" || version_ok=0
  if [ "${old_replicas:-0}" -lt 1 ]; then
    echo "the app was not running before this deploy; leaving it at 0" >&2
  elif [ "$jobs_ok" != 1 ] || [ -n "$left" ]; then
    echo "LEAVING THE APP AT 0: could not confirm the Jobs are gone ($left)." >&2
    echo "Check: kubectl -n $ns get jobs,pods; then compare alembic_version with '${version_before:-(none)}'." >&2
  elif [ "$version_ok" != 1 ] || [ "$now" != "$version_before" ]; then
    echo "LEAVING THE APP AT 0: alembic_version is '$now', was '${version_before:-(none)}' (or could not be read)." >&2
    echo "The migration may have committed, so the old image may not match the schema. Either re-run the" >&2
    echo "pipeline to finish this deploy, or restore $backup_file (documentation/guides/k3s.md, Rollback)." >&2
  else
    echo "Jobs deleted and alembic_version unchanged (${now:-(none)}); restoring the previous app (replicas=$old_replicas)" >&2
    kubectl -n "$ns" scale deployment/issue-tracker --replicas="$old_replicas" >&2
  fi
  rm -rf "$tmp"
  exit "$rc"
}
trap on_failure EXIT
trap 'exit 130' INT TERM

if [ -n "$app_exists" ]; then
  phase="maintenance window"
  if [ "${old_replicas:-0}" -ge 1 ]; then
    kubectl -n "$ns" scale deployment/issue-tracker --replicas=0
  fi
  # Even at 0 replicas a Terminating pod may still write: wait it out. Abort before the backup
  # if an app pod is still there at the timeout, or the pod list can't be read.
  wait_app_gone "$timeout"
  echo "maintenance: app scaled to 0 for backup + migrate"
fi

# 2. Pre-deploy backup. Job specs are immutable, so replace the previous run's Job.
phase="backup"
kubectl -n "$ns" delete job issue-tracker-backup-predeploy issue-tracker-migrate --ignore-not-found --wait=true
kubectl -n "$ns" apply -f "$tmp/jobs.yaml" -l app.kubernetes.io/component=backup
wait_job issue-tracker-backup-predeploy

# 3. Forward-only migration (its init container re-checks $backup_file).
phase="migrate"
kubectl -n "$ns" apply -f "$tmp/jobs.yaml" -l app.kubernetes.io/component=migrate
wait_job issue-tracker-migrate

# 4. App rollout (the manifest sets replicas back to 1). From here on the schema may be new,
# so a failure no longer brings the old app back.
trap - INT TERM
trap 'rm -rf "$tmp"' EXIT
kubectl -n "$ns" apply -f "$tmp/app.yaml"
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout="${timeout}s"

# 5. Health from inside the pod (the pipeline also checks the ingress URL).
body="$(kubectl -n "$ns" exec deploy/issue-tracker -c app -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read().decode())")"
echo "health: $body"
python3 -c 'import json,sys; sys.exit(0 if json.loads(sys.argv[1]).get("database") == "ok" else 1)' "$body"
echo "deployed $image to $ns"
