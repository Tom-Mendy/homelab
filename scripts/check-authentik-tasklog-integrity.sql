-- Run with psql -X -v ON_ERROR_STOP=1 against the Authentik database.
-- This check is read-only and prints no log contents or user information.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '30s';

DO $check$
DECLARE
    orphan_count bigint;
    fk_oid oid;
BEGIN
    SELECT count(*) INTO orphan_count
    FROM public.authentik_tasks_tasklog AS logs
    WHERE logs.task_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM public.authentik_tasks_task AS tasks
          WHERE tasks.message_id = logs.task_id
      );

    IF orphan_count <> 0 THEN
        RAISE EXCEPTION 'Authentik task-log integrity failed: % orphan rows',
            orphan_count;
    END IF;

    SELECT oid INTO fk_oid
    FROM pg_constraint
    WHERE conrelid = 'public.authentik_tasks_tasklog'::regclass
      AND confrelid = 'public.authentik_tasks_task'::regclass
      AND conname = 'authentik_tasks_task_task_id_a82f0835_fk_authentik'
      AND contype = 'f' AND convalidated;

    IF fk_oid IS NULL THEN
        RAISE EXCEPTION 'Authentik task-log foreign key is missing or unvalidated';
    END IF;

    IF (SELECT count(*) FROM pg_trigger
        WHERE tgconstraint = fk_oid AND tgenabled IN ('O', 'A')) <> 4 THEN
        RAISE EXCEPTION 'Authentik task-log foreign-key triggers are not enabled';
    END IF;

    IF current_setting('session_replication_role') <> 'origin' THEN
        RAISE EXCEPTION 'Connection bypasses normal constraint enforcement';
    END IF;

    RAISE NOTICE 'Authentik task-log integrity passed';
END $check$;

COMMIT;
