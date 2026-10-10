-- Seed script: adds 5 demo events in November 2026 to the Events/calendar module.
-- Useful for testing the Events page and for demos, since a fresh database
-- otherwise has no events at all.
--
-- Run after create_database.sql / populate_database.sql have already been run:
--   psql -U postgres -d whariki_connect -f seed_demo_events.sql
--
-- Assumes the standard seeded users/classrooms from populate_database.sql
-- (user_id 1 = Admin, user_id 2 = Teacher in Piwakawaka Room, user_id 4 = Teacher
-- in Kereru Room, user_id 6 = Teacher in Tui Room). Adjust the created_by /
-- classroom values below if your data differs.

INSERT INTO Events (created_by, classroom, title, description, event_type, event_date, end_date) VALUES
(1, 'All classrooms', 'Whānau Photo Day', 'Professional photographer on site for family and individual portraits.', 'photo_day', '2026-11-05', NULL),
(6, 'Tui Room', 'Botanic Gardens Excursion', 'Tui Room outing to the Botanic Gardens. Please bring a sunhat and water bottle.', 'excursion', '2026-11-11', NULL),
(1, 'All classrooms', 'Centre Closed - Professional Development Day', 'Centre closed for staff training. No children on site.', 'closed_day', '2026-11-17', NULL),
(2, 'Piwakawaka Room', 'Matariki Art Showcase', 'Piwakawaka Room is displaying tamariki artwork for whānau to view after pickup.', 'other', '2026-11-20', NULL),
(4, 'Kereru Room', 'Wellington Zoo Trip', 'Two-day exploration trip, overnight stay not included - pickup both days as normal.', 'excursion', '2026-11-24', '2026-11-25');
