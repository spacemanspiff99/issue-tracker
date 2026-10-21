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
mutate restore.sh "success, schema changed: app left at 0 (N1)" \
  'schema_same="$(same_version "$v_before" "$v_after")"' \
  'schema_same=1'
mutate restore.sh "another restore started meanwhile (N4)" \
  'if [ -n "$active" ]; then' \
  'if false; then'
mutate restore.sh "lock already held: refuses, leaves the lock (N-1)" \
  'if ! kubectl -n "$ns" create configmap "$lock" --from-literal=job="$job" > /dev/null; then' \
  'if ! { kubectl -n "$ns" create configmap "$lock" --from-literal=job="$job" > /dev/null || true; }; then'
mutate restore.sh "lock kept while the Job may still run (N-1)" \
  'job_may_run=1
kubectl -n "$ns" create -f - <<YAML' \
  'job_may_run=0
kubectl -n "$ns" create -f - <<YAML'
mutate restore.sh "lock released after a successful restore (N-1)" \
  'elif [ -n "$holder" ] && ! kubectl -n "$ns" delete configmap "$lock" --ignore-not-found > /dev/null; then' \
  'elif false; then'
mutate restore-job.sh "failed transaction logs the version after the failure (N-3)" \
  'echo "alembic_version after failed restore: $after"' \
  ':'
mutate restore.sh "failed, version changed: app left at 0 (N-3)" \
  'if [ "$committed" = no ] && [ "$(same_version "$v_before" "$v_failed")" = 1 ]; then' \
  'if [ "$committed" = no ]; then'
mutate restore.sh "success, duplicate version lines: app left at 0 (N-4)" \
  'if [ "$(grep -c "^$1: " <<< "$logs" || true)" = 1 ]; then' \
  'if true; then'
# Issue 0048.
mutate restore.sh "live restore pod without a Job: refuses before anything (0048 #1)" \
  "| awk '\$1 != \"\" && \$2 != \"Succeeded\" && \$2 != \"Failed\" {printf \"%s \", \$1}'" \
  "| awk '{}'"
mutate restore.sh "lock now held by another run: not released (0048 #2)" \
  'elif [ -n "$holder" ] && [ "$holder" != "$job" ]; then' \
  'elif false; then'
mutate deploy.sh "deploy: lock now held by another run: not released (0048 #2)" \
  'elif [ -n "$holder" ] && [ "$holder" != "$lock_holder" ]; then' \
  'elif false; then'
mutate deploy.sh "deploy: lock held by a restore: refuses (0048 #3)" \
  'if ! kubectl -n "$ns" create configmap "$lock" --from-literal=job="$lock_holder" > /dev/null; then' \
  'if ! { kubectl -n "$ns" create configmap "$lock" --from-literal=job="$lock_holder" > /dev/null || true; }; then'
mutate deploy.sh "deploy: lock kept when the Jobs may still run (0048 #3)" \
  '[ "$jobs_ok" != 1 ] || [ -n "$left" ] || job_may_run=0' \
  'job_may_run=0'
mutate deploy.sh "deploy: lock released after a successful deploy (0048 #3)" \
  'elif [ -n "$holder" ] && ! kubectl -n "$ns" delete configmap "$lock" --ignore-not-found > /dev/null; then' \
  'elif false; then'
mutate restore.sh "Job failed before COMMIT (control)" \
  'revision unchanged (${v_before}); app back to' \
  'the database is unchanged; app back to'

# 0048 #4: without kubectl, fail-closed.sh must stop with exit 2 and say why, not run any case
# (and not report a failure that hides the real cause). Checked on the script and on a mutant.
needs_kubectl() {  # needs_kubectl <fail-closed.sh>: 0 if it exits 2 with "needs kubectl"
  local out rc
  out="$(PATH=/nonexistent /bin/bash "$1" 2>&1)" && rc=0 || rc=$?
  [ "$rc" = 2 ] && grep -q "needs kubectl" <<< "$out"
}
if needs_kubectl "$k8s/tests/fail-closed.sh"; then
  echo "ok   fail-closed.sh without kubectl: exit 2, \"needs kubectl\""
else
  echo "BAD  fail-closed.sh without kubectl did not exit 2 with \"needs kubectl\""; bad=$((bad + 1))
fi
rm -rf "$work/k8s"; cp -r "$k8s" "$work/k8s"
sed -i '/needs kubectl on PATH/d' "$work/k8s/tests/fail-closed.sh"
if needs_kubectl "$work/k8s/tests/fail-closed.sh"; then
  echo "BAD  the kubectl check still passes with the check removed"; bad=$((bad + 1))
else
  echo "ok   the kubectl check catches: check removed"
fi

if [ "$bad" -ne 0 ]; then
  echo "$bad mutation(s) not caught" >&2
  exit 1
fi
echo "all mutations caught"
