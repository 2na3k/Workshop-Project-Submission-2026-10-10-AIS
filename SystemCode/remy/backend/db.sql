CREATE DATABASE remy_main;

\c remy_main

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS app_user (
    username      TEXT        PRIMARY KEY,
    password_hash TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT app_user_username_format
        CHECK (username ~ '^[a-z0-9][a-z0-9._-]{2,31}$'),
    CONSTRAINT app_user_password_hash_not_plaintext
        CHECK (length(password_hash) >= 20)
);

DROP TRIGGER IF EXISTS app_user_set_updated_at ON app_user;
CREATE TRIGGER app_user_set_updated_at
    BEFORE UPDATE ON app_user
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

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

    CONSTRAINT preference_special_diet_known
        CHECK (special_diet IS NULL
               OR special_diet IN ('halal', 'vegetarian', 'meat'))
);

DROP TRIGGER IF EXISTS preference_set_updated_at ON preference;
CREATE TRIGGER preference_set_updated_at
    BEFORE UPDATE ON preference
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS preference_special_diet_idx
    ON preference (special_diet)
    WHERE special_diet IS NOT NULL;

CREATE INDEX IF NOT EXISTS preference_cuisine_idx
    ON preference (cuisine)
    WHERE cuisine IS NOT NULL;

COMMIT;
