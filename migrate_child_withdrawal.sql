-- =========================================================================
-- Migration: child withdrawal workflow. A withdrawn child is never deleted
-- - all their history stays intact - just hidden from the default lists.
--
--   psql -U postgres -d whariki_connect -f migrate_child_withdrawal.sql
--
-- Not needed if you are rebuilding the database from scratch -
-- create_database.sql already contains this.
-- =========================================================================

ALTER TABLE Children ADD COLUMN IF NOT EXISTS enrolment_status VARCHAR(20) NOT NULL DEFAULT 'enrolled';
ALTER TABLE Children DROP CONSTRAINT IF EXISTS children_enrolment_status_check;
ALTER TABLE Children ADD CONSTRAINT children_enrolment_status_check
  CHECK (enrolment_status IN ('enrolled', 'withdrawn'));

ALTER TABLE Children ADD COLUMN IF NOT EXISTS withdrawal_date DATE;
ALTER TABLE Children ADD COLUMN IF NOT EXISTS withdrawal_notes VARCHAR(255);
