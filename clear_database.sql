-- Clears all data but keeps the table structure - handy for re-seeding
-- during development. Run with:
--   psql -U postgres -d whariki_connect -f clear_database.sql

TRUNCATE TABLE Notifications, Accident_Forms, Messages, Attendance,
    Learning_Stories, Parent_Child, Children, Users, Centres, Params
    RESTART IDENTITY CASCADE;
