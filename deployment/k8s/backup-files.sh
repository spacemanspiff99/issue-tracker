#!/usr/bin/env bash
# List, copy off, or copy onto the backup PVC through a short-lived helper pod.
#
# Usage:
#   deployment/k8s/backup-files.sh <uat|prod> list
#   deployment/k8s/backup-files.sh <uat|prod> get <remote path under /backups> <local dir>
#   deployment/k8s/backup-files.sh <uat|prod> get-latest <local dir>    # newest daily + pre-migration
#   deployment/k8s/backup-files.sh <uat|prod> put <local file> <name>   # lands in /backups/imports/<name>
set -euo pipefail
env_name="${1:?usage: backup-files.sh <uat|prod> <list|get|get-latest|put> ...}"
action="${2:?action required}"
case "$env_name" in
  uat) ns=issue-tracker-uat ;;
  prod) ns=issue-tracker ;;
  *) echo "unknown environment: $env_name" >&2; exit 2 ;;
esac
expected_context="${EXPECTED_CONTEXT:-issue-tracker-$env_name}"
context="$(kubectl config current-context)"
[ "$context" = "$expected_context" ] || { echo "refusing: context '$context', expected '$expected_context'" >&2; exit 2; }

pod="issue-tracker-backup-files-$$"
read_only=true
[ "$action" = put ] && read_only=false
kubectl -n "$ns" apply -f - > /dev/null <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: $pod
  labels: {app.kubernetes.io/name: issue-tracker, app.kubernetes.io/component: backup-files}
spec:
  restartPolicy: Never
  containers:
    - name: files
      image: postgres:16
      command: ["sleep", "1800"]
      volumeMounts: [{name: backups, mountPath: /backups, readOnly: $read_only}]
  volumes:
    - name: backups
      persistentVolumeClaim: {claimName: issue-tracker-backups}
YAML
trap 'kubectl -n "$ns" delete pod "$pod" --wait=false > /dev/null 2>&1 || true' EXIT
kubectl -n "$ns" wait --for=condition=Ready "pod/$pod" --timeout=180s > /dev/null

fetch() {  # $1 remote file, $2 local dir
  mkdir -p "$2"
  kubectl -n "$ns" cp "$pod:$1" "$2/$(basename "$1")" > /dev/null
  kubectl -n "$ns" exec "$pod" -- pg_restore -l "$1" > /dev/null
  echo "copied $1 -> $2/$(basename "$1") ($(du -h "$2/$(basename "$1")" | cut -f1))"
}

case "$action" in
  list) kubectl -n "$ns" exec "$pod" -- sh -c 'ls -lt /backups/* 2>/dev/null; df -h /backups' ;;
  get) fetch "${3:?remote path}" "${4:?local dir}" ;;
  get-latest)
    for d in daily pre-migration; do
      f="$(kubectl -n "$ns" exec "$pod" -- sh -c "ls -1t /backups/$d/*.dump 2>/dev/null | head -1")"
      if [ -n "$f" ]; then fetch "$f" "${3:?local dir}"; else echo "no $d dumps yet"; fi
    done ;;
  put)
    src="${3:?local file}" name="${4:?name}"
    [[ "$name" =~ ^[A-Za-z0-9._-]+\.dump$ ]] || { echo "name must look like something.dump" >&2; exit 2; }
    pg_restore -l "$src" > /dev/null 2>&1 || echo "note: local pg_restore unavailable or failed; checking in the pod" >&2
    kubectl -n "$ns" exec "$pod" -- mkdir -p /backups/imports
    kubectl -n "$ns" cp "$src" "$pod:/backups/imports/$name" > /dev/null
    kubectl -n "$ns" exec "$pod" -- pg_restore -l "/backups/imports/$name" > /dev/null
    echo "uploaded $src -> /backups/imports/$name (readable by pg_restore)" ;;
  *) echo "unknown action: $action" >&2; exit 2 ;;
esac
