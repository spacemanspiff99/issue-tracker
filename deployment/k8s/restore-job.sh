#!/usr/bin/env bash
# Runs INSIDE the restore Job pod (restore.sh mounts it from a ConfigMap). Do not run by hand.
# Env: DUMP, REQUIRE_EMPTY (0|1), POSTGRES_USER, POSTGRES_DB, PGHOST, PGPASSWORD, and
# RESTORE_TEST_DELAY_SECONDS (tests only: pause before the transaction).
set -euo pipefail

# Tests only: BACKUPS_ROOT stands in for /backups (the Job never sets it).
root="${BACKUPS_ROOT:-/backups}"

# The schema revision, "(none)" if there is no alembic_version table; any other error fails.
# restore.sh compares these log lines to decide whether the app may come back.
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
# Read first, so any later failure can be compared against it: on a failure the EXIT trap
# re-reads the revision, and restore.sh brings the app back only if it is unchanged.
before="$(db_version)"
echo "alembic_version before restore: $before"

pin="$root/restoring/${HOSTNAME:-local}.dump" pinned=0
on_exit() {
  local rc=$? after
  [ "$pinned" = 0 ] || rm -f "$pin"
  if [ "$rc" -ne 0 ]; then
    after="$(db_version)" || after="(unreadable)"
    echo "alembic_version after failed restore: $after"
  fi
  exit "$rc"
}
trap on_exit EXIT

# Pin the dump with a hard link outside the pruned folders, so no prune (the daily CronJob, the
# backup Job, or this script) can remove it while it is being restored. Restore from the pin.
# A killed restore Job leaks its pin (bash as PID 1 ignores SIGTERM, so a SIGKILL skips the EXIT
# trap), and the hard link keeps that dump's space in use. restore.sh holds the restore lock and
# refuses while any other restore pod is live, so every pin here but this Job's own is leaked.
mkdir -p "$root/restoring"
for p in "$root"/restoring/*.dump; do
  [ -e "$p" ] && [ "$p" != "$pin" ] || continue
  rm -fv "$p"
done
rm -f "$pin"
ln "$DUMP" "$pin"
pinned=1
pg_restore -l "$pin" > /dev/null

echo "dump readable: $DUMP ($(pg_restore -l "$pin" | grep -c ' TABLE DATA ' || true) tables with data)"

# Safety copy of the database as it is now, before anything is dropped. Pruning to the newest 5
# happens only after a successful restore, and never removes the dump being restored.
mkdir -p "$root/pre-restore"
rm -f "$root"/pre-restore/*.partial
safety="$root/pre-restore/$(date -u +%Y%m%dT%H%M%SZ)-${HOSTNAME:-local}.dump"
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
ls -1t "$root"/pre-restore/*.dump | grep -vxF "$DUMP" | tail -n +6 | xargs -r rm -fv || true
after="$(db_version)" || after="(unreadable)"
echo "alembic_version after restore: $after"
