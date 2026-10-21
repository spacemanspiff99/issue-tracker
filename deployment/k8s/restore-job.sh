#!/usr/bin/env bash
# Runs INSIDE the restore Job pod (restore.sh mounts it from a ConfigMap). Do not run by hand.
# Env: DUMP, REQUIRE_EMPTY (0|1), POSTGRES_USER, POSTGRES_DB, PGHOST, PGPASSWORD, and
# RESTORE_TEST_DELAY_SECONDS (tests only: pause before the transaction).
set -euo pipefail

# Pin the dump with a hard link outside the pruned folders, so no prune (the daily CronJob, the
# backup Job, or this script) can remove it while it is being restored. Restore from the pin.
# Restores never overlap (restore.sh refuses while one is active), so any pin already here was leaked
# by a killed restore Job: bash as PID 1 ignores SIGTERM, so a SIGKILL (grace period, OOM) skips the
# EXIT trap. Clear those first; each leaked hard link would otherwise keep its dump's space in use.
mkdir -p /backups/restoring
rm -fv /backups/restoring/*.dump
pin="/backups/restoring/${HOSTNAME:-local}.dump"
ln "$DUMP" "$pin"
trap 'rm -f "$pin"' EXIT
pg_restore -l "$pin" > /dev/null

# The schema revision, "(none)" if there is no alembic_version table; any other error fails.
# restore.sh compares the before and after lines to decide whether the app may come back.
db_version() {
  local present
  present="$(psql -X -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select to_regclass('public.alembic_version') is not null")" || return 1
  if [ "$present" = t ]; then
    psql -X -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
      -c "select coalesce(string_agg(version_num, ',' order by version_num), '(empty)') from alembic_version" || return 1
  else
    echo '(none)'
  fi
}
before="$(db_version)"
echo "alembic_version before restore: $before"
echo "dump readable: $DUMP ($(pg_restore -l "$pin" | grep -c ' TABLE DATA ' || true) tables with data)"

# Safety copy of the database as it is now, before anything is dropped. Pruning to the newest 5
# happens only after a successful restore, and never removes the dump being restored.
mkdir -p /backups/pre-restore
rm -f /backups/pre-restore/*.partial
safety="/backups/pre-restore/$(date -u +%Y%m%dT%H%M%SZ)-${HOSTNAME:-local}.dump"
test ! -e "$safety"
pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$safety.partial"
pg_restore -l "$safety.partial" > /dev/null
mv "$safety.partial" "$safety"
echo "safety dump of the current database: $safety"

sleep "${RESTORE_TEST_DELAY_SECONDS:-0}"

# One transaction: guard, schema drop, full restore. Any error rolls everything back.
# The guard uses EXECUTE so a missing projects table is not planned (and so not an error).
{
  echo 'BEGIN;'
  echo 'SET LOCAL client_min_messages = warning;'
  if [ "$REQUIRE_EMPTY" = 1 ]; then
    cat <<'SQL'
DO $guard$
DECLARE n bigint := 0;
BEGIN
  IF to_regclass('public.projects') IS NOT NULL THEN
    EXECUTE 'SELECT count(*) FROM public.projects' INTO n;
  END IF;
  IF n > 0 THEN
    RAISE EXCEPTION 'projects has % row(s); refusing to overwrite', n;
  END IF;
END
$guard$;
SQL
  fi
  echo 'DROP SCHEMA public CASCADE;'
  echo 'CREATE SCHEMA public;'
  pg_restore --no-owner --no-privileges -f - "$pin"
  echo 'COMMIT;'
} | psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null
echo "restore committed"
ls -1t /backups/pre-restore/*.dump | grep -vxF "$DUMP" | tail -n +6 | xargs -r rm -fv || true
after="$(db_version)" || after="(unreadable)"
echo "alembic_version after restore: $after"
