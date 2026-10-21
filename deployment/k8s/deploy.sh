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

# Never start while a previous backup or migration is still running.
for job in issue-tracker-backup-predeploy issue-tracker-migrate; do
  active="$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.active}' 2> /dev/null || true)"
  if [ "${active:-0}" -ge 1 ]; then
    echo "refusing: job $job is still active in $ns; inspect it before deploying again" >&2
    exit 1
  fi
done

# 1. Everything except the app Deployment/Service/Ingress (ConfigMap, Postgres, PVCs, CronJob).
kubectl -n "$ns" apply -f "$tmp/app.yaml" -l 'app.kubernetes.io/component!=web'
kubectl -n "$ns" rollout status statefulset/issue-tracker-postgres --timeout="${timeout}s"

# 2. Pre-deploy backup. Job specs are immutable, so replace the previous run's Job.
kubectl -n "$ns" delete job issue-tracker-backup-predeploy issue-tracker-migrate --ignore-not-found --wait=true
kubectl -n "$ns" apply -f "$tmp/jobs.yaml" -l app.kubernetes.io/component=backup
wait_job issue-tracker-backup-predeploy

# 3. Forward-only migration (its init container re-checks $backup_file).
kubectl -n "$ns" apply -f "$tmp/jobs.yaml" -l app.kubernetes.io/component=migrate
wait_job issue-tracker-migrate

# 4. App rollout.
kubectl -n "$ns" apply -f "$tmp/app.yaml"
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout="${timeout}s"

# 5. Health from inside the pod (the pipeline also checks the ingress URL).
body="$(kubectl -n "$ns" exec deploy/issue-tracker -c app -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read().decode())")"
echo "health: $body"
python3 -c 'import json,sys; sys.exit(0 if json.loads(sys.argv[1]).get("database") == "ok" else 1)' "$body"
echo "deployed $image to $ns"
