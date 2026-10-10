-- =========================================================================
-- Migration: profile photos + daily routine records
-- Adds the new columns and table WITHOUT dropping existing data.
--
--   psql -U postgres -d whariki_connect -f migrate_avatars_and_routines.sql
--
-- Not needed if you are building the database from scratch -
-- create_database.sql already contains all of this.
-- =========================================================================

ALTER TABLE Users    ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255);
ALTER TABLE Children ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255);

CREATE TABLE IF NOT EXISTS Routines (
    routine_id      SERIAL PRIMARY KEY,
    child_id        INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    recorded_by     INT REFERENCES Users(user_id),
    date            DATE NOT NULL,
    category        VARCHAR(20) NOT NULL CHECK (category IN ('meal', 'toileting')),
    routine_type    VARCHAR(40) NOT NULL,
    outcome         VARCHAR(40),
    recorded_at     TIMESTAMP NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_routines_child_date ON Routines (child_id, date);
