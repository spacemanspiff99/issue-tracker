#!/usr/bin/env bash
# Run the Playwright workflow suite (tests/e2e, issue 0014) from a one-off pod built from the
# deployed image, against the in-namespace Service. A separate pod keeps Chromium's memory out
# of the app pod. Screenshots are copied to $E2E_OUT (default artifacts/e2e-k8s).
# The suite creates "E2E ..." data and never wipes the DB; it refuses to run in production.
#
# Credentials: E2E_ADMIN_USERNAME from the ConfigMap's ADMIN_USERNAME; password from the
# issue-tracker-app Secret key E2E_ADMIN_PASSWORD, falling back to ADMIN_INITIAL_PASSWORD.
#
# Usage: deployment/k8s/e2e.sh <namespace>
set -euo pipefail
ns="${1:?usage: e2e.sh <namespace>}"
[ "$ns" = issue-tracker ] && { echo "refusing to run e2e against production" >&2; exit 2; }
out="${E2E_OUT:-artifacts/e2e-k8s}"
timeout="${E2E_TIMEOUT_SECONDS:-900}"
pod=issue-tracker-e2e

image="$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.template.spec.containers[?(@.name=="app")].image}')"
kubectl -n "$ns" delete pod "$pod" --ignore-not-found --wait=true
kubectl -n "$ns" apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: $pod
  labels:
    app.kubernetes.io/name: issue-tracker
    app.kubernetes.io/component: e2e
spec:
  restartPolicy: Never
  imagePullSecrets:
    - name: ghcr-pull
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
  containers:
    - name: e2e
      image: $image
      command:
        - sh
        - -c
        - |
          if [ ! -d tests/e2e ]; then echo "no tests/e2e in image"; echo 99 > /tmp/e2e-exit; sleep 600; exit 0; fi
          RUN_BROWSER_UAT=1 python -m pytest -p no:cacheprovider -rfEX tests/e2e/
          echo \$? > /tmp/e2e-exit
          sleep 600
      env:
        - name: E2E_BASE_URL
          value: http://issue-tracker
        - name: E2E_ADMIN_USERNAME
          valueFrom:
            configMapKeyRef: {name: issue-tracker-config, key: ADMIN_USERNAME}
        - name: E2E_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef: {name: issue-tracker-app, key: E2E_ADMIN_PASSWORD, optional: true}
        - name: ADMIN_INITIAL_PASSWORD
          valueFrom:
            secretKeyRef: {name: issue-tracker-app, key: ADMIN_INITIAL_PASSWORD, optional: true}
      resources:
        requests:
          cpu: 100m
          memory: 256Mi
        limits:
          memory: 1Gi
YAML
trap 'kubectl -n "$ns" delete pod "$pod" --ignore-not-found --wait=false > /dev/null' EXIT

kubectl -n "$ns" wait --for=condition=Ready "pod/$pod" --timeout=300s
deadline=$((SECONDS + timeout))
until code="$(kubectl -n "$ns" exec "$pod" -- cat /tmp/e2e-exit 2> /dev/null)"; do
  (( SECONDS < deadline )) || { kubectl -n "$ns" logs "$pod" >&2; echo "e2e timed out" >&2; exit 1; }
  sleep 5
done
kubectl -n "$ns" logs "$pod"

if [ "$code" = 99 ]; then
  echo "FAIL: deployed image has no tests/e2e, so the browser suite cannot run" >&2
  exit 1
fi
mkdir -p "$out"
kubectl -n "$ns" cp "$pod:/app/artifacts/e2e" "$out" > /dev/null || echo "warning: no screenshots copied" >&2
echo "screenshots: $(find "$out" -name '*.png' | wc -l) in $out"
[ "$code" = 0 ] || { echo "e2e failed (pytest exit $code)" >&2; exit 1; }
[ "$(find "$out" -name '*.png' | wc -l)" -gt 0 ] || { echo "e2e passed but produced no screenshots" >&2; exit 1; }
echo "e2e passed"
