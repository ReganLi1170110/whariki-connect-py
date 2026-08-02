-- =========================================================================
-- Whariki Connect - static reference data
-- Run this AFTER create_database.sql and BEFORE generate_data.py:
--   psql -U postgres -d whariki_connect -f populate_database.sql
--
-- This file only contains fixed, hand-written lookup values - things like
-- classroom names and curriculum strands that don't need a password hash
-- or any generation logic. Accounts, children, and demo content are
-- created separately by generate_data.py, since those need bcrypt to hash
-- passwords before they can be inserted.
-- =========================================================================

-- Centres (ECE preschools using the platform). Only one today, but the
-- sign-up form's "choose your centre" list reads from this table, so a
-- second centre can be added later with a single INSERT and no code change.
INSERT INTO Centres (name) VALUES
('Sunshine Preschool');

-- Classrooms (also referenced by generate_data.py when creating teachers
-- and children, so the two files describe a shared, consistent set of rooms)
INSERT INTO Params (param_type, param_value, description) VALUES
('classroom', 'Piwakawaka Room', 'Nursery - roughly 0 to 2 years'),
('classroom', 'Kereru Room',     'Toddlers - roughly 2 to 3 years'),
('classroom', 'Tui Room',        'Preschool - roughly 3 to 5 years');

-- Te Whariki curriculum strands, used to tag each learning story
INSERT INTO Params (param_type, param_value, description) VALUES
('curriculum_strand', 'Wellbeing',      'Mana atua - the health and wellbeing of the child is protected and nurtured'),
('curriculum_strand', 'Belonging',      'Mana whenua - children and their families feel a sense of belonging'),
('curriculum_strand', 'Contribution',   'Mana tangata - opportunities for learning are equitable, and each child''s contribution is valued'),
('curriculum_strand', 'Communication',  'Mana reo - the languages and symbols of their own and other cultures are promoted and protected'),
('curriculum_strand', 'Exploration',    'Mana aoturoa - the child learns through active exploration of the environment');

-- Te Whariki learning outcomes (20 in total). `description` holds the strand
-- each outcome belongs to, so the learning story form can group them.
INSERT INTO Params (param_type, param_value, description) VALUES
('learning_outcome', 'Keeping themselves healthy and caring for themselves', 'Wellbeing'),
('learning_outcome', 'Managing themselves and expressing their feelings and needs', 'Wellbeing'),
('learning_outcome', 'Keeping themselves and others safe from harm', 'Wellbeing'),
('learning_outcome', 'Making connections between people, places and things in their world', 'Belonging'),
('learning_outcome', 'Taking part in caring for this place', 'Belonging'),
('learning_outcome', 'Understanding how things work here and adapting to change', 'Belonging'),
('learning_outcome', 'Showing a sense of responsibility', 'Belonging'),
('learning_outcome', 'Treating others fairly and including them in play', 'Contribution'),
('learning_outcome', 'Recognising and appreciating their own ability to learn', 'Contribution'),
('learning_outcome', 'Using a range of strategies and skills to play and learn with others', 'Contribution'),
('learning_outcome', 'Using gesture and movement to express themselves', 'Communication'),
('learning_outcome', 'Understanding oral language and using it for a range of purposes', 'Communication'),
('learning_outcome', 'Enjoying hearing stories and retelling and creating them', 'Communication'),
('learning_outcome', 'Recognising print symbols and concepts and using them with enjoyment, meaning and purpose', 'Communication'),
('learning_outcome', 'Recognising mathematical symbols and concepts and using them with enjoyment, meaning and purpose', 'Communication'),
('learning_outcome', 'Expressing their feelings and ideas using a wide range of materials and modes', 'Communication'),
('learning_outcome', 'Playing, imagining, inventing and experimenting', 'Exploration'),
('learning_outcome', 'Moving confidently and challenging themselves physically', 'Exploration'),
('learning_outcome', 'Using a range of strategies for reasoning and problem solving', 'Exploration'),
('learning_outcome', 'Making sense of their worlds by generating and refining working theories', 'Exploration');

-- Nature-of-injury options for the accident/incident form
INSERT INTO Params (param_type, param_value) VALUES
('injury_nature', 'Graze / scrape'),
('injury_nature', 'Cut / laceration'),
('injury_nature', 'Bruise'),
('injury_nature', 'Bump to the head'),
('injury_nature', 'Bite'),
('injury_nature', 'Sprain / strain'),
('injury_nature', 'Burn / scald'),
('injury_nature', 'Foreign object'),
('injury_nature', 'Allergic reaction'),
('injury_nature', 'Other');

-- How the parent was contacted after an incident
INSERT INTO Params (param_type, param_value) VALUES
('contact_method', 'Phone'),
('contact_method', 'Email'),
('contact_method', 'In person'),
('contact_method', 'Other');

-- Accident/incident form body-part options, used to populate the dropdown
-- on the accident form instead of a free-text field
INSERT INTO Params (param_type, param_value) VALUES
('accident_body_part', 'Head'),
('accident_body_part', 'Face'),
('accident_body_part', 'Arm'),
('accident_body_part', 'Hand / fingers'),
('accident_body_part', 'Leg'),
('accident_body_part', 'Knee'),
('accident_body_part', 'Foot / toes'),
('accident_body_part', 'Torso'),
('accident_body_part', 'Other');

-- Attendance status options
INSERT INTO Params (param_type, param_value) VALUES
('attendance_status', 'present'),
('attendance_status', 'absent'),
('attendance_status', 'sick'),
('attendance_status', 'on_leave');
