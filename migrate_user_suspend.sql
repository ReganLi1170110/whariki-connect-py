-- =========================================================================
-- Migration: adds a 'suspended' account status, for admins to deactivate a
-- user (e.g. staff left) without deleting their history. Distinct from
-- 'rejected', which means a sign-up request itself was declined.
--
--   psql -U postgres -d whariki_connect -f migrate_user_suspend.sql
--
-- Not needed if you are rebuilding the database from scratch -
-- create_database.sql already contains this.
-- =========================================================================

ALTER TABLE Users DROP CONSTRAINT IF EXISTS users_status_check;
ALTER TABLE Users ADD CONSTRAINT users_status_check
  CHECK (status IN ('pending', 'approved', 'rejected', 'suspended'));
