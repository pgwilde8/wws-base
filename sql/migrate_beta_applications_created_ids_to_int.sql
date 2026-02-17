-- Convert created_user_id and created_trucker_profile_id from UUID to INTEGER
-- so they match webwise.users.id and webwise.trucker_profiles.id.
-- Run: psql "$DATABASE_URL" -f sql/migrate_beta_applications_created_ids_to_int.sql
--
-- Safe: only alters if columns are still UUID; no error if already INTEGER.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'webwise' AND table_name = 'beta_driver_applications'
      AND column_name = 'created_user_id' AND data_type = 'uuid'
  ) THEN
    EXECUTE 'ALTER TABLE webwise.beta_driver_applications ALTER COLUMN created_user_id TYPE INTEGER USING NULL::INTEGER';
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'webwise' AND table_name = 'beta_driver_applications'
      AND column_name = 'created_trucker_profile_id' AND data_type = 'uuid'
  ) THEN
    EXECUTE 'ALTER TABLE webwise.beta_driver_applications ALTER COLUMN created_trucker_profile_id TYPE INTEGER USING NULL::INTEGER';
  END IF;
END $$;
