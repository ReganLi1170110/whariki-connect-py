-- =========================================================================
-- Migration: teacher timesheets.
-- Adds the new table WITHOUT dropping any existing data.
--
--   psql -U postgres -d whariki_connect -f migrate_timesheet.sql
--
-- Not needed if you are rebuilding the database from scratch -
-- create_database.sql already contains this.
-- =========================================================================

CREATE TABLE IF NOT EXISTS Timesheet_Entries (
    entry_id        SERIAL PRIMARY KEY,
    teacher_id      INT NOT NULL REFERENCES Users(user_id),
    work_date       DATE NOT NULL,
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    break_minutes   INT NOT NULL DEFAULT 0,
    notes           VARCHAR(255),
    status          VARCHAR(20) NOT NULL DEFAULT 'submitted'
                    CHECK (status IN ('submitted', 'approved')),
    last_edited_by  INT REFERENCES Users(user_id),
    created_at      TIMESTAMP NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (teacher_id, work_date)
);

CREATE INDEX IF NOT EXISTS idx_timesheet_teacher_date ON Timesheet_Entries (teacher_id, work_date);
