#!/usr/bin/env bash
# Proves fail-closed.sh would catch a regression: each mutation below re-introduces a fail-open
# pattern (`|| true`, an unchecked read, a forced replica count) into a copy of the scripts, and
# the named fail-closed.sh case must then FAIL. A mutation that no longer applies is an error too,
# so this list stays in step with the scripts.
#
# Usage: deployment/k8s/tests/fail-closed-mutations.sh   (no cluster; same needs as fail-closed.sh)
set -euo pipefail
k8s="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
bad=0

# mutate <file> <case text for FC_ONLY> <python: old> <python: new>
mutate() {
  local file="$1" case="$2" old="$3" new="$4" copy="$work/k8s"
  rm -rf "$copy"; cp -r "$k8s" "$copy"
  if ! python3 - "$copy/$file" "$old" "$new" <<'PY'
import sys
path, old, new = sys.argv[1:4]
s = open(path).read()
if s.count(old) != 1:
    sys.exit(f"mutation target not found exactly once in {path}: {old!r}")
open(path, "w").write(s.replace(old, new))
PY
  then
    echo "BAD  mutation for '$case' no longer applies"; bad=$((bad + 1)); return
  fi
  if FC_ONLY="$case" bash "$copy/tests/fail-closed.sh" > "$work/out" 2>&1; then
    echo "BAD  '$case' still passes with: $new"; bad=$((bad + 1))
  elif grep -q "^FAIL .*$case" "$work/out"; then
    echo "ok   '$case' catches: $new"
  else
    echo "BAD  '$case' errored without reporting the case:"; sed 's/^/    /' "$work/out"; bad=$((bad + 1))
  fi
}

mutate restore.sh "Job failed, logs unreadable" \
  'logs="$(kubectl -n "$ns" logs "job/$job" 2>&1)" || logs_ok=0' \
  'logs="$(kubectl -n "$ns" logs "job/$job" 2>&1 || true)"'
mutate restore.sh "timeout, Job delete fails" \
  'if kubectl -n "$ns" delete job "$job" --wait=true --cascade=foreground --timeout=120s; then' \
  'if kubectl -n "$ns" delete job "$job" --wait=true --cascade=foreground --timeout=120s || true; then'
mutate restore.sh "app at 0, --keep-app-down, failed before COMMIT (B1)" \
  '[ "$keep_down" = 0 ] && restore_app_to="$prev_replicas"' \
  'restore_app_to="$advise_replicas"'
mutate restore.sh "Job status unreadable (timeout)" \
  "jsonpath='{.status.succeeded}/{.status.failed}' --request-timeout=10s)\"; then" \
  "jsonpath='{.status.succeeded}/{.status.failed}' --request-timeout=10s || echo 1/)\"; then"
mutate restore.sh "backup Job active? (NB-a)" \
  "active=\"\$(kubectl -n \"\$ns\" get job \"\$job\" --ignore-not-found -o jsonpath='{.status.active}')\"" \
  "active=\"\$(kubectl -n \"\$ns\" get job \"\$job\" --ignore-not-found -o jsonpath='{.status.active}' 2> /dev/null || true)\""
mutate deploy.sh "…and on_failure can't list Jobs" \
  '--ignore-not-found -o name 2>&1)" || jobs_ok=0' \
  '--ignore-not-found -o name 2> /dev/null || true)"'
mutate deploy.sh "…and on_failure can't read version" \
  'now="$(db_version 2>&1)" || version_ok=0' \
  'now="$(db_version 2> /dev/null || true)"'
mutate deploy.sh "app pods gone?" \
  'if ! pods="$(kubectl -n "$ns" get pods -l app.kubernetes.io/component=web -o name --request-timeout=10s)"; then' \
  'if ! pods="$(kubectl -n "$ns" get pods -l app.kubernetes.io/component=web -o name --request-timeout=10s || true)"; then'

if [ "$bad" -ne 0 ]; then
  echo "$bad mutation(s) not caught" >&2
  exit 1
fi
echo "all mutations caught"
