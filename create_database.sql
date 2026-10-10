-- =========================================================================
-- Whariki Connect - database schema (COMP693 Project)
-- Run this once against an empty database:
--   psql -U postgres -d whariki_connect -f create_database.sql
-- =========================================================================

DROP TABLE IF EXISTS Immunizations CASCADE;
DROP TABLE IF EXISTS Routines CASCADE;
DROP TABLE IF EXISTS Notifications CASCADE;
DROP TABLE IF EXISTS Accident_Forms CASCADE;
DROP TABLE IF EXISTS Messages CASCADE;
DROP TABLE IF EXISTS Library_Documents CASCADE;
DROP TABLE IF EXISTS Authorized_Pickups CASCADE;
DROP TABLE IF EXISTS Timesheet_Entries CASCADE;
DROP TABLE IF EXISTS Events CASCADE;
DROP TABLE IF EXISTS Announcements CASCADE;
DROP TABLE IF EXISTS Attendance CASCADE;
DROP TABLE IF EXISTS Learning_Stories CASCADE;
DROP TABLE IF EXISTS Parent_Child CASCADE;
DROP TABLE IF EXISTS Children CASCADE;
DROP TABLE IF EXISTS Users CASCADE;
DROP TABLE IF EXISTS Centres CASCADE;
DROP TABLE IF EXISTS Params CASCADE;

-- =========================
-- CENTRES (ECE centres/preschools using the platform. Only one row today
-- - "Sunshine Preschool" - but modelled as its own table so the sign-up
-- form's "choose your centre" dropdown, and the schema generally, are
-- ready to support more than one centre later without a redesign.)
-- =========================
CREATE TABLE Centres (
    centre_id       SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================
-- PARAMS (static lookup/reference data - classrooms, curriculum strands,
-- and anything else the app offers as a fixed set of options. Populated
-- by populate_database.sql, separately from the dynamically-generated
-- accounts in generate_data.py.)
-- =========================
CREATE TABLE Params (
    id              SERIAL PRIMARY KEY,
    param_type      VARCHAR(50) NOT NULL,
    param_value     VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'Active',
    description     VARCHAR(255)
);

-- =========================
-- USERS (parents, teachers, and one super admin)
-- =========================
CREATE TABLE Users (
    user_id         SERIAL PRIMARY KEY,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('Admin', 'Teacher', 'Parent')),
    full_name       VARCHAR(120) NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    phone           VARCHAR(30),
    classroom       VARCHAR(50),      -- only used for Teacher accounts
    centre_id       INT REFERENCES Centres(centre_id),
    -- 'pending' = self-registered via /signup, awaiting admin approval.
    -- 'approved' = can log in and use the platform (all seeded accounts
    -- are created as 'approved' directly, since an admin made them).
    -- 'rejected' = signup request was declined by an admin.
    -- 'suspended' = was approved, later deactivated by an admin (e.g. staff
    -- left) - distinct from 'rejected', which means the original request
    -- itself was never accepted.
    status          VARCHAR(20) NOT NULL DEFAULT 'approved'
                    CHECK (status IN ('pending', 'approved', 'rejected', 'suspended')),
    -- Filename of an uploaded profile photo in app/static/uploads/.
    -- NULL means fall back to the initials avatar.
    avatar_url      VARCHAR(255),
    -- Set when the user requests a password reset; cleared once used or on
    -- successful login. A NULL/expired token means the reset link is dead.
    reset_token             VARCHAR(64),
    reset_token_expires     TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_reset_token ON Users (reset_token);

-- =========================
-- CHILDREN
-- =========================
CREATE TABLE Children (
    child_id            SERIAL PRIMARY KEY,
    first_name          VARCHAR(80) NOT NULL,
    last_name           VARCHAR(80) NOT NULL,
    date_of_birth       DATE NOT NULL,
    classroom           VARCHAR(50) NOT NULL,
    emergency_contact   VARCHAR(150),
    emergency_phone     VARCHAR(30),
    notes               TEXT,
    -- Filename of an uploaded photo in app/static/uploads/, set by a parent.
    avatar_url          VARCHAR(255),
    -- Health & safety, shown prominently on the child's profile so any
    -- teacher covering the room can see it at a glance. Free text rather
    -- than a fixed enum, since real allergy/medical notes vary too much
    -- to usefully constrain (severity, instructions, EpiPen location...).
    allergies             TEXT,
    medical_conditions    TEXT,
    medications           TEXT,
    dietary_requirements  TEXT,
    medical_notes         TEXT,
    -- 'enrolled' = active; 'withdrawn' = left the centre. Withdrawal is
    -- never a hard delete - all of a withdrawn child's history (learning
    -- stories, attendance, accident forms...) is kept, just hidden from the
    -- default lists so it doesn't clutter day-to-day use.
    enrolment_status      VARCHAR(20) NOT NULL DEFAULT 'enrolled'
                         CHECK (enrolment_status IN ('enrolled', 'withdrawn')),
    withdrawal_date        DATE,
    withdrawal_notes       VARCHAR(255),
    created_at          TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================
-- PARENT <-> CHILD (many-to-many: each child usually has 2 parents)
-- =========================
CREATE TABLE Parent_Child (
    parent_id       INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    child_id        INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    relationship    VARCHAR(30) DEFAULT 'parent',
    PRIMARY KEY (parent_id, child_id)
);

-- =========================
-- LEARNING STORIES
-- =========================
CREATE TABLE Learning_Stories (
    story_id        SERIAL PRIMARY KEY,
    child_id        INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    teacher_id      INT NOT NULL REFERENCES Users(user_id),
    title           VARCHAR(200) NOT NULL,
    content         TEXT NOT NULL,
    -- Filename of an uploaded image stored in app/static/uploads/
    media_url       TEXT,
    strands         TEXT[] DEFAULT '{}',   -- Te Whariki curriculum strands
    outcomes        TEXT[] DEFAULT '{}',   -- Te Whariki learning outcomes
    -- 'draft' = saved but not visible to parents; 'published' = visible.
    status          VARCHAR(20) NOT NULL DEFAULT 'published'
                    CHECK (status IN ('draft', 'published')),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================
-- ATTENDANCE
-- =========================
CREATE TABLE Attendance (
    attendance_id   SERIAL PRIMARY KEY,
    child_id        INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    check_in_time   TIMESTAMP,
    check_out_time  TIMESTAMP,
    status          VARCHAR(20) NOT NULL DEFAULT 'present'
                    CHECK (status IN ('present', 'absent', 'sick', 'on_leave')),
    recorded_by     INT REFERENCES Users(user_id),
    UNIQUE (child_id, date)
);

-- =========================
-- ANNOUNCEMENTS (one teacher/admin action fans out to many parents as
-- individual Messages rows - see broadcast_id below - but this row is the
-- single source of truth for "what was sent, to which room, by whom, when"
-- so it can be listed/audited without recounting Messages.)
-- =========================
CREATE TABLE Announcements (
    announcement_id     SERIAL PRIMARY KEY,
    sender_id            INT NOT NULL REFERENCES Users(user_id),
    -- The classroom it was sent to, or 'All classrooms' (Admin only).
    classroom             VARCHAR(50) NOT NULL,
    content                TEXT NOT NULL,
    recipient_count        INT NOT NULL DEFAULT 0,
    created_at              TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================
-- EVENTS (centre/classroom calendar: excursions, photo day, closed days...)
-- Shown to everyone in scope rather than sent as a one-off message, so it
-- stays visible ahead of the date rather than scrolling out of an inbox.
-- =========================
CREATE TABLE Events (
    event_id        SERIAL PRIMARY KEY,
    created_by      INT NOT NULL REFERENCES Users(user_id),
    -- Same 'All classrooms' sentinel Announcements uses for centre-wide.
    classroom       VARCHAR(50) NOT NULL,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    event_type      VARCHAR(30) NOT NULL DEFAULT 'other'
                    CHECK (event_type IN ('excursion', 'photo_day', 'closed_day', 'other')),
    event_date      DATE NOT NULL,
    end_date        DATE,  -- NULL for a single-day event
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================
-- TIMESHEET ENTRIES
-- Actual hours a teacher worked on a given day - separate from Attendance
-- (which tracks children, not staff) and separate from any future rostering
-- feature (which would be "planned" hours rather than "actual"). Teachers
-- fill in and edit their own entries; once an admin approves an entry (e.g.
-- for payroll) the teacher can no longer change it, though an admin always
-- can.
-- =========================
-- =========================
-- AUTHORIZED PICKUPS
-- Who besides the registered parents is allowed to collect a child -
-- distinct from emergency_contact (one name for emergencies), this is a
-- proper list staff can check against at pickup time. Maintained by the
-- child's own parent, or an admin.
-- =========================
-- =========================
-- LIBRARY DOCUMENTS
-- Admin-uploaded reference PDFs, on top of the built-in set that ships with
-- the repo (app/static/library/manifest.json, untouched by this table).
-- The two sources are merged when the library page is rendered.
-- =========================
CREATE TABLE Library_Documents (
    document_id     SERIAL PRIMARY KEY,
    slug            VARCHAR(150) NOT NULL UNIQUE,
    title           VARCHAR(200) NOT NULL,
    description     VARCHAR(500),
    category        VARCHAR(50) NOT NULL,
    filename        VARCHAR(255) NOT NULL,
    size_mb         NUMERIC(6,2),
    uploaded_by     INT REFERENCES Users(user_id),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE Authorized_Pickups (
    pickup_id       SERIAL PRIMARY KEY,
    child_id        INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    full_name       VARCHAR(150) NOT NULL,
    phone           VARCHAR(30),
    relationship    VARCHAR(100),  -- e.g. 'Grandmother', 'Family friend', 'Babysitter'
    notes           VARCHAR(255),  -- e.g. 'Has photo ID on file', 'Tuesdays only'
    added_by        INT REFERENCES Users(user_id),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_authorized_pickups_child ON Authorized_Pickups (child_id);

CREATE TABLE Timesheet_Entries (
    entry_id        SERIAL PRIMARY KEY,
    teacher_id      INT NOT NULL REFERENCES Users(user_id),
    work_date       DATE NOT NULL,
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    break_minutes   INT NOT NULL DEFAULT 0,
    notes           VARCHAR(255),
    -- 'submitted' = the teacher's own entry, still editable by them.
    -- 'approved' = an admin has finalised it (e.g. for payroll); only an
    -- admin can change it from here.
    status          VARCHAR(20) NOT NULL DEFAULT 'submitted'
                    CHECK (status IN ('submitted', 'approved')),
    last_edited_by  INT REFERENCES Users(user_id),
    created_at      TIMESTAMP NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (teacher_id, work_date)
);
CREATE TABLE Messages (
    message_id              SERIAL PRIMARY KEY,
    sender_id                INT NOT NULL REFERENCES Users(user_id),
    receiver_id               INT NOT NULL REFERENCES Users(user_id),
    child_id                 INT REFERENCES Children(child_id),
    content                   TEXT NOT NULL,
    linked_story_id           INT REFERENCES Learning_Stories(story_id),
    linked_attendance_id      INT REFERENCES Attendance(attendance_id),
    linked_accident_id        INT,  -- FK added below, once Accident_Forms exists
    -- Set when this copy of the message was fanned out from an announcement
    -- broadcast rather than typed directly to this one recipient.
    is_broadcast              BOOLEAN NOT NULL DEFAULT false,
    broadcast_id               INT REFERENCES Announcements(announcement_id),
    is_read                   BOOLEAN NOT NULL DEFAULT false,
    created_at                TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================
-- ACCIDENT / INCIDENT FORMS
-- =========================
CREATE TABLE Accident_Forms (
    accident_id                 SERIAL PRIMARY KEY,
    child_id                    INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    teacher_id                  INT NOT NULL REFERENCES Users(user_id),

    -- Incident details
    incident_date               DATE NOT NULL,
    incident_time               TIME,
    location                    VARCHAR(200) NOT NULL,
    nature_of_injury            VARCHAR(200),
    body_part                   VARCHAR(120),
    description                 TEXT NOT NULL,

    -- Caregiver response
    action_taken                TEXT NOT NULL,      -- first aid provided
    additional_information      TEXT,

    -- Parent contact block (mirrors the paper accident report)
    parent_contacted            BOOLEAN NOT NULL DEFAULT false,
    parent_contacted_name       VARCHAR(150),
    contacted_by                VARCHAR(150),       -- which staff member made contact
    contact_method              VARCHAR(30),        -- Phone / Email / Other
    contact_method_other        VARCHAR(120),
    parent_contacted_time       TIME,
    other_actions_taken         TEXT,

    -- Compliance flags
    medical_attention_needed    BOOLEAN NOT NULL DEFAULT false,
    notifiable_event            BOOLEAN NOT NULL DEFAULT false,

    -- 'draft' = saved by the teacher, not yet visible to parents.
    -- 'submitted' = finalised and visible to the child's parents.
    status                      VARCHAR(20) NOT NULL DEFAULT 'submitted'
                                CHECK (status IN ('draft', 'submitted')),
    provider_signature          VARCHAR(150),       -- typed signature of the teacher
    teacher_signed_at           TIMESTAMP,
    parent_acknowledged_at      TIMESTAMP,
    parent_acknowledged_by      INT REFERENCES Users(user_id),
    created_at                  TIMESTAMP NOT NULL DEFAULT now()
);

ALTER TABLE Messages
    ADD CONSTRAINT fk_messages_accident
    FOREIGN KEY (linked_accident_id) REFERENCES Accident_Forms(accident_id);

-- =========================
-- NOTIFICATIONS
-- =========================
CREATE TABLE Notifications (
    notification_id     SERIAL PRIMARY KEY,
    user_id              INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    type                  VARCHAR(30) NOT NULL
                          CHECK (type IN ('learning_story', 'message', 'attendance', 'accident_form', 'event')),
    content               TEXT NOT NULL,
    related_id            INT,
    is_read               BOOLEAN NOT NULL DEFAULT false,
    created_at            TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================
-- ROUTINES (daily care records: meals and toileting)
-- Teachers log these through the day; parents see only their own children's.
-- =========================
CREATE TABLE Routines (
    routine_id      SERIAL PRIMARY KEY,
    child_id        INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    recorded_by     INT REFERENCES Users(user_id),
    date            DATE NOT NULL,
    -- 'meal' covers morning tea / lunch / afternoon tea;
    -- 'toileting' covers nappy changes and independent toilet use.
    category        VARCHAR(20) NOT NULL CHECK (category IN ('meal', 'toileting')),
    -- For meals: 'Morning tea' | 'Lunch' | 'Afternoon tea'
    -- For toileting: 'Nappy change' | 'Toilet'
    routine_type    VARCHAR(40) NOT NULL,
    -- Meals: 'All' | 'Most' | 'Some' | 'None'
    -- Toileting: 'Wet' | 'Soiled' | 'Dry' | 'Success' | 'Accident'
    outcome         VARCHAR(40),
    recorded_at     TIMESTAMP NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

-- =========================
-- IMMUNIZATIONS (NZ National Immunisation Schedule records per child)
-- =========================
CREATE TABLE Immunizations (
    immunization_id     SERIAL PRIMARY KEY,
    child_id              INT NOT NULL REFERENCES Children(child_id) ON DELETE CASCADE,
    recorded_by            INT REFERENCES Users(user_id),
    vaccine_name             VARCHAR(150) NOT NULL,   -- e.g. 'MMR', 'DTaP-IPV-Hib-HepB'
    dose_label                 VARCHAR(30),             -- e.g. '6 weeks', 'Booster', '2nd dose'
    date_given                   DATE,
    -- 'completed' = given; 'scheduled' = booked but not yet due/given;
    -- 'overdue' = past the recommended age and not yet given;
    -- 'exempt' = parent has filed a conscientious/medical exemption.
    status                         VARCHAR(20) NOT NULL DEFAULT 'completed'
                                   CHECK (status IN ('completed', 'scheduled', 'overdue', 'exempt')),
    notes                           TEXT,
    created_at                       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_routines_child_date ON Routines (child_id, date);
CREATE INDEX idx_params_type ON Params (param_type);
CREATE INDEX idx_users_status ON Users (status);
CREATE INDEX idx_children_classroom ON Children (classroom);
CREATE INDEX idx_stories_child ON Learning_Stories (child_id);
CREATE INDEX idx_attendance_child_date ON Attendance (child_id, date);
CREATE INDEX idx_messages_thread ON Messages (sender_id, receiver_id);
CREATE INDEX idx_messages_broadcast ON Messages (broadcast_id);
CREATE INDEX idx_accidents_child ON Accident_Forms (child_id);
CREATE INDEX idx_accidents_date ON Accident_Forms (incident_date);
CREATE INDEX idx_stories_teacher ON Learning_Stories (teacher_id);
CREATE INDEX idx_notifications_user ON Notifications (user_id, is_read);
CREATE INDEX idx_immunizations_child ON Immunizations (child_id);
CREATE INDEX idx_announcements_classroom ON Announcements (classroom);
CREATE INDEX idx_events_classroom ON Events (classroom);
CREATE INDEX idx_events_date ON Events (event_date);
CREATE INDEX idx_timesheet_teacher_date ON Timesheet_Entries (teacher_id, work_date);
