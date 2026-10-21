#!/usr/bin/env bash
# Runs INSIDE the restore Job pod (restore.sh mounts it from a ConfigMap). Do not run by hand.
# Env: DUMP, REQUIRE_EMPTY (0|1), POSTGRES_USER, POSTGRES_DB, PGHOST, PGPASSWORD, and
# RESTORE_TEST_DELAY_SECONDS (tests only: pause before the transaction).
set -euo pipefail

pg_restore -l "$DUMP" > /dev/null
echo "dump readable: $DUMP ($(pg_restore -l "$DUMP" | grep -c ' TABLE DATA ' || true) tables with data)"

# Safety copy of the database as it is now, before anything is dropped. Keep the newest 5.
mkdir -p /backups/pre-restore
rm -f /backups/pre-restore/*.partial
safety="/backups/pre-restore/$(date -u +%Y%m%dT%H%M%SZ)-${HOSTNAME:-local}.dump"
test ! -e "$safety"
pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$safety.partial"
pg_restore -l "$safety.partial" > /dev/null
mv "$safety.partial" "$safety"
echo "safety dump of the current database: $safety"
ls -1t /backups/pre-restore/*.dump | tail -n +6 | xargs -r rm -fv

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
  pg_restore --no-owner --no-privileges -f - "$DUMP"
  echo 'COMMIT;'
} | psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null
echo "restore committed"
psql -X -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'select version_num from alembic_version' \
  | sed 's/^/alembic_version after restore: /' || echo "alembic_version after restore: (none)"
