-- =========================================================================
-- Migration: authorized pickup people per child.
-- Adds the new table WITHOUT dropping any existing data.
--
--   psql -U postgres -d whariki_connect -f migrate_authorized_pickups.sql
--
-- Not needed if you are rebuilding the database from scratch -
-- create_database.sql already contains this.
-- =========================================================================

CREATE TABLE IF NOT EXISTS Authorized_Pickups (
    pickup_id       SERIAL PRIMARY KEY,
    child_id        INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    full_name       VARCHAR(150) NOT NULL,
    phone           VARCHAR(30),
    relationship    VARCHAR(100),
    notes           VARCHAR(255),
    added_by        INT REFERENCES Users(user_id),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_authorized_pickups_child ON Authorized_Pickups (child_id);
