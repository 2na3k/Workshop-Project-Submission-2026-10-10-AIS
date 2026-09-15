-- Remy application database - PostgreSQL 14+
--
-- This is the operational store for accounts and preferences. It is separate
-- from the DuckDB/ducklake analytics warehouse in ../../data-preparation, which
-- holds recipes, foods and prices.
--
-- Run through psql, which this file needs for the \c meta-command:
--     psql -U postgres -v ON_ERROR_STOP=1 -f api/sql/schema.sql
--
-- CREATE DATABASE cannot run inside a transaction block, so it sits outside the
-- BEGIN below. Re-running the whole file errors on the CREATE DATABASE (there is
-- no IF NOT EXISTS for it); everything after \c is idempotent, so to re-apply
-- just the tables, run this file from \c onwards against an existing database.

CREATE DATABASE remy
    ENCODING 'UTF8'
    LC_COLLATE 'en_US.UTF-8'
    LC_CTYPE 'en_US.UTF-8'
    TEMPLATE template0;

COMMENT ON DATABASE remy IS 'Remy meal planner: accounts and food preferences.';

\c remy

BEGIN;

-- Keeps updated_at honest without the application having to remember.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;


-- ---------------------------------------------------------------------------
-- app_user
-- ---------------------------------------------------------------------------
-- Named app_user because USER is a reserved word in SQL: a table called "user"
-- would need double quotes at every single call site.

CREATE TABLE IF NOT EXISTS app_user (
    username      TEXT        PRIMARY KEY,
    password_hash TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT app_user_username_format
        CHECK (username ~ '^[a-z0-9][a-z0-9._-]{2,31}$'),

    -- A bare length floor, enough to catch a plaintext password written here by
    -- mistake. The hash itself is verified by the application.
    CONSTRAINT app_user_password_hash_not_plaintext
        CHECK (length(password_hash) >= 20)
);

COMMENT ON TABLE  app_user IS 'Registered accounts.';
COMMENT ON COLUMN app_user.username IS
    'Natural key. Lowercase, 3-32 chars; normalise before insert so Alice and alice cannot both register.';
COMMENT ON COLUMN app_user.password_hash IS
    'Full PHC string from a slow KDF, e.g. argon2id: $argon2id$v=19$m=...$salt$hash. The salt and parameters live inside this value, so no separate salt column. Never store a plaintext or fast-hash (MD5/SHA) password here.';

DROP TRIGGER IF EXISTS app_user_set_updated_at ON app_user;
CREATE TRIGGER app_user_set_updated_at
    BEFORE UPDATE ON app_user
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();


-- ---------------------------------------------------------------------------
-- preference
-- ---------------------------------------------------------------------------
-- One row per user: username is both the primary key and the foreign key, which
-- is what makes the relationship 1:1 rather than 1:many.

CREATE TABLE IF NOT EXISTS preference (
    username           TEXT        PRIMARY KEY
                                   REFERENCES app_user (username)
                                   ON DELETE CASCADE
                                   ON UPDATE CASCADE,
    special_diet       TEXT,
    cuisine            TEXT,
    preferred_nutrient TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Mirrors the three options on the onboarding screen
    -- (frontend/src/components/preferences-form.tsx). NULL means not answered.
    CONSTRAINT preference_special_diet_known
        CHECK (special_diet IS NULL
               OR special_diet IN ('halal', 'vegetarian', 'meat'))
);

COMMENT ON TABLE  preference IS 'Food preferences captured during onboarding; at most one row per user.';
COMMENT ON COLUMN preference.username IS
    'FK to app_user. ON DELETE CASCADE so deleting an account takes its preferences with it.';
COMMENT ON COLUMN preference.special_diet IS
    'Dietary restriction: halal, vegetarian or meat. NULL until onboarding is completed.';
COMMENT ON COLUMN preference.cuisine IS
    'Preferred cuisine, e.g. Peranakan. Single value - see the note at the end of this file if multi-select is needed.';
COMMENT ON COLUMN preference.preferred_nutrient IS
    'Nutrient to optimise for, e.g. protein or fibre. Free-form; values come from the nutrient names in the analytics warehouse.';

DROP TRIGGER IF EXISTS preference_set_updated_at ON preference;
CREATE TRIGGER preference_set_updated_at
    BEFORE UPDATE ON preference
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- The recommender filters on these before it ever looks at a username.
CREATE INDEX IF NOT EXISTS preference_special_diet_idx
    ON preference (special_diet)
    WHERE special_diet IS NOT NULL;

CREATE INDEX IF NOT EXISTS preference_cuisine_idx
    ON preference (cuisine)
    WHERE cuisine IS NOT NULL;

COMMIT;


-- ---------------------------------------------------------------------------
-- Note on multi-select cuisines
-- ---------------------------------------------------------------------------
-- The onboarding screen lets a user pick several cuisines, but `cuisine` above
-- is a single TEXT column as specified. To hold more than one, replace it with
-- a child table rather than a comma-separated string:
--
--     CREATE TABLE preference_cuisine (
--         username TEXT NOT NULL
--                  REFERENCES app_user (username)
--                  ON DELETE CASCADE ON UPDATE CASCADE,
--         cuisine  TEXT NOT NULL,
--         PRIMARY KEY (username, cuisine)
--     );
