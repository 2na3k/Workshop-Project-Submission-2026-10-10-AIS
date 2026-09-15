
BEGIN;

-- Refuses to run anywhere except `recall`, so this cannot itself become the
-- mistake it is cleaning up.
DO $guard$
BEGIN
    IF current_database() <> 'recall' THEN
        RAISE EXCEPTION
            'Connected to database "%", expected "recall". Reconnect to recall and re-run.',
            current_database();
    END IF;
END
$guard$;

-- Refuses to drop tables that have rows in them. Both were empty when this was
-- written; if that has changed, something is using them and you should look
-- before deleting.
DO $check$
DECLARE
    n bigint;
BEGIN
    IF to_regclass('public.app_user') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM public.app_user' INTO n;
        IF n > 0 THEN
            RAISE EXCEPTION 'app_user has % row(s) - not dropping. Inspect it first.', n;
        END IF;
    END IF;

    IF to_regclass('public.preference') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM public.preference' INTO n;
        IF n > 0 THEN
            RAISE EXCEPTION 'preference has % row(s) - not dropping. Inspect it first.', n;
        END IF;
    END IF;
END
$check$;

-- preference first: it has the foreign key into app_user.
DROP TABLE IF EXISTS public.preference;
DROP TABLE IF EXISTS public.app_user;

-- Dropping the tables removes their triggers, which leaves this function with
-- no dependants. Plain DROP (not CASCADE) so that if anything in recall did
-- come to depend on it, this errors instead of quietly breaking that thing.
DROP FUNCTION IF EXISTS public.set_updated_at();

COMMIT;
