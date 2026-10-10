-- Clears all data but keeps the table structure - handy for re-seeding
-- during development. Run with:
--   psql -U postgres -d whariki_connect -f clear_database.sql

TRUNCATE TABLE Library_Documents, Authorized_Pickups, Immunizations, Routines, Notifications, Accident_Forms, Events,
    Timesheet_Entries, Announcements, Messages, Attendance,
    Learning_Stories, Parent_Child, Children, Users, Centres, Params
    RESTART IDENTITY CASCADE;
