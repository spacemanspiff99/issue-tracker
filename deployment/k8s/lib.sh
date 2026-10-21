# Sourced by deploy.sh and restore.sh (not run on its own). Needs $ns.

# Restore pods not yet Succeeded/Failed: a pod can outlive its Job, or be made by hand. One may be
# restoring from a pin in /backups/restoring, so no deploy or new restore may start beside it.
# Prints their names (space-separated); fails if the pods can't be listed.
live_restore_pods() {
  kubectl -n "$ns" get pods -l app.kubernetes.io/component=restore \
    -o jsonpath='{range .items[*]}{.metadata.name} {.status.phase}{"\n"}{end}' \
    | awk '$1 != "" && $2 != "Succeeded" && $2 != "Failed" {printf "%s ", $1}'
}
