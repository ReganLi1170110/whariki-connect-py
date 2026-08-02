-- =========================================================================
-- Whariki Connect - database schema (COMP693 Project)
-- Run this once against an empty database:
--   psql -U postgres -d whariki_connect -f create_database.sql
-- =========================================================================

DROP TABLE IF EXISTS Notifications CASCADE;
DROP TABLE IF EXISTS Accident_Forms CASCADE;
DROP TABLE IF EXISTS Messages CASCADE;
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
    status          VARCHAR(20) NOT NULL DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

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
-- MESSAGES (parent <-> teacher chat)
-- =========================
CREATE TABLE Messages (
    message_id              SERIAL PRIMARY KEY,
    sender_id                INT NOT NULL REFERENCES Users(user_id),
    receiver_id               INT NOT NULL REFERENCES Users(user_id),
    child_id                 INT REFERENCES Children(child_id),
    content                   TEXT NOT NULL,
    linked_story_id           INT REFERENCES Learning_Stories(story_id),
    linked_attendance_id      INT REFERENCES Attendance(attendance_id),
    linked_accident_id        INT,  -- FK added below, once Accident_Forms exists
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
                          CHECK (type IN ('learning_story', 'message', 'attendance', 'accident_form')),
    content               TEXT NOT NULL,
    related_id            INT,
    is_read               BOOLEAN NOT NULL DEFAULT false,
    created_at            TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_params_type ON Params (param_type);
CREATE INDEX idx_users_status ON Users (status);
CREATE INDEX idx_children_classroom ON Children (classroom);
CREATE INDEX idx_stories_child ON Learning_Stories (child_id);
CREATE INDEX idx_attendance_child_date ON Attendance (child_id, date);
CREATE INDEX idx_messages_thread ON Messages (sender_id, receiver_id);
CREATE INDEX idx_accidents_child ON Accident_Forms (child_id);
CREATE INDEX idx_accidents_date ON Accident_Forms (incident_date);
CREATE INDEX idx_stories_teacher ON Learning_Stories (teacher_id);
CREATE INDEX idx_notifications_user ON Notifications (user_id, is_read);
