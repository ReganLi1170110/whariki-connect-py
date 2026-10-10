-- =========================================================================
-- Migration: child health & safety fields, immunisation records, and
-- broadcast announcements. Adds new columns/tables WITHOUT dropping any
-- existing data.
--
--   psql -U postgres -d whariki_connect -f migrate_health_and_announcements.sql
--
-- Not needed if you are rebuilding the database from scratch -
-- create_database.sql already contains all of this.
-- =========================================================================

-- --- Child health & safety fields ----------------------------------------
ALTER TABLE Children ADD COLUMN IF NOT EXISTS allergies TEXT;
ALTER TABLE Children ADD COLUMN IF NOT EXISTS medical_conditions TEXT;
ALTER TABLE Children ADD COLUMN IF NOT EXISTS medications TEXT;
ALTER TABLE Children ADD COLUMN IF NOT EXISTS dietary_requirements TEXT;
ALTER TABLE Children ADD COLUMN IF NOT EXISTS medical_notes TEXT;

-- --- Immunisation records --------------------------------------------------
CREATE TABLE IF NOT EXISTS Immunizations (
    immunization_id     SERIAL PRIMARY KEY,
    child_id              INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    recorded_by            INT REFERENCES Users(user_id),
    vaccine_name             VARCHAR(150) NOT NULL,
    dose_label                 VARCHAR(30),
    date_given                   DATE,
    status                         VARCHAR(20) NOT NULL DEFAULT 'completed'
                                   CHECK (status IN ('completed', 'scheduled', 'overdue', 'exempt')),
    notes                           TEXT,
    created_at                       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_immunizations_child ON Immunizations (child_id);

-- --- Broadcast announcements ----------------------------------------------
CREATE TABLE IF NOT EXISTS Announcements (
    announcement_id     SERIAL PRIMARY KEY,
    sender_id             INT NOT NULL REFERENCES Users(user_id),
    classroom              VARCHAR(50) NOT NULL,
    content                  TEXT NOT NULL,
    recipient_count          INT NOT NULL DEFAULT 0,
    created_at                TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_announcements_classroom ON Announcements (classroom);

ALTER TABLE Messages ADD COLUMN IF NOT EXISTS is_broadcast BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE Messages ADD COLUMN IF NOT EXISTS broadcast_id INT REFERENCES Announcements(announcement_id);

CREATE INDEX IF NOT EXISTS idx_messages_broadcast ON Messages (broadcast_id);
