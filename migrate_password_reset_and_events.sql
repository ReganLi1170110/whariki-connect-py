-- =========================================================================
-- Migration: password reset tokens + events/calendar module.
-- Adds new columns/tables WITHOUT dropping any existing data.
--
--   psql -U postgres -d whariki_connect -f migrate_password_reset_and_events.sql
--
-- Not needed if you are rebuilding the database from scratch -
-- create_database.sql already contains all of this.
-- =========================================================================

-- --- Password reset ---------------------------------------------------------
ALTER TABLE Users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(64);
ALTER TABLE Users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON Users (reset_token);

-- --- Events / calendar -------------------------------------------------------
CREATE TABLE IF NOT EXISTS Events (
    event_id        SERIAL PRIMARY KEY,
    created_by      INT NOT NULL REFERENCES Users(user_id),
    -- 'All classrooms' (the same sentinel Announcements already uses) means
    -- centre-wide; otherwise a specific room name.
    classroom       VARCHAR(50) NOT NULL,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    -- 'excursion' | 'photo_day' | 'closed_day' | 'other'
    event_type      VARCHAR(30) NOT NULL DEFAULT 'other',
    event_date      DATE NOT NULL,
    end_date        DATE,  -- NULL for a single-day event
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_classroom ON Events (classroom);
CREATE INDEX IF NOT EXISTS idx_events_date ON Events (event_date);

-- Allow the new notification type used when an event is created.
ALTER TABLE Notifications DROP CONSTRAINT IF EXISTS notifications_type_check;
ALTER TABLE Notifications ADD CONSTRAINT notifications_type_check
  CHECK (type IN ('learning_story', 'message', 'attendance', 'accident_form', 'event'));
