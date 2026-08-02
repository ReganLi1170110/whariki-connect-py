"""
Data generator for the Whariki Connect database.
===================================================
Run AFTER create_database.sql and populate_database.sql (this script reads
classroom names and curriculum strands from the Params table that
populate_database.sql fills in - it does not hardcode them).

Populates the database with:
  - 1 super admin
  - 6 teachers (2 assigned to each of 3 classrooms)
  - 20 children (basic profile info), spread across the 3 classrooms
  - 40 parents (2 parents linked to each child)
  - A small amount of demo content (today's attendance, a few learning
    stories, and one accident form) so the app is explorable immediately.

Every account uses the SAME password (see SEED_PASSWORD below). It is
hashed with bcrypt before being stored - the plain text password is never
written to the database.

Usage:
    python generate_data.py
"""
import random
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
from flask import Flask
from flask_bcrypt import Bcrypt

from app.db import connect

# ---------------------------------------------------------------------------
# Database connection (mirrors connect.py, same as the rest of the app)
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": connect.dbhost,
    "port": connect.dbport,
    "dbname": connect.dbname,
    "user": connect.dbuser,
    "password": connect.dbpass,
}

SEED_PASSWORD = 'Sunnypreschool123'

_flask_app = Flask(__name__)
flask_bcrypt = Bcrypt(_flask_app)

TEACHER_NAMES = [
    'Sarah Thompson', 'Aroha Ngata', 'Michael Chen',
    'Emily Wilson', 'Jayden Wiremu', 'Priya Patel',
]

CHILDREN = [
    ('Oliver', 'Smith'), ('Charlotte', 'Brown'), ('Manaia', 'Rangi'),
    ('Amelia', 'Taylor'), ('Nikau', 'Walker'), ('Isla', 'Anderson'),
    ('Kaia', 'Wiremu'), ('Noah', 'Clarke'), ('Ruby', 'Mitchell'),
    ('Levi', 'Parata'), ('Mia', 'Robinson'), ('Ethan', 'Nguyen'),
    ('Ariana', 'Faamausili'), ('Jack', 'Campbell'), ('Aria', 'Patel'),
    ('Tane', 'Henare'), ('Grace', 'Wilson'), ('Leo', 'Kim'),
    ('Willow', 'Edwards'), ('Hunter', 'Ropata'),
]

PARENT_FIRST_NAMES = [
    'James', 'Emma', 'Liam', 'Sophie', 'Daniel', 'Hannah', 'Matthew', 'Olivia',
    'David', 'Grace', 'Ben', 'Chloe', 'Sam', 'Ella', 'Josh', 'Zoe', 'Ryan',
    'Lucy', 'Adam', 'Kate', 'Marcus', 'Nina', 'Tom', 'Anna', 'Paul', 'Rachel',
    'Simon', 'Laura', 'Chris', 'Megan', 'Andrew', 'Jess', 'Mark', 'Amy',
    'Nathan', 'Holly', 'Peter', 'Sarah', 'Luke', 'Claire',
]

STORY_TEMPLATES = [
    {'title': 'Exploring the sandpit',
     'content': "{name} spent most of the morning at the sandpit, carefully filling and emptying "
                "buckets to build a row of towers. When another child joined, {name} shifted over "
                "to make room and handed across a spade without being asked. Together they talked "
                "about which tower was tallest and tried adding water to see if the sand would hold "
                "its shape better."},
    {'title': 'Painting at the easel',
     'content': "{name} chose the easel this morning and worked steadily for nearly twenty minutes. "
                "After mixing blue and yellow and noticing the paint turned green, {name} paused, "
                "looked up and said 'look what happened!' - then deliberately repeated the mix to "
                "check it would happen again."},
    {'title': 'Mat time storytelling',
     'content': "During mat time {name} sat right at the front and joined in with the repeated lines "
                "of the story. Afterwards {name} took the book to the reading corner, turned the pages "
                "in order, and retold the story in their own words to a small group of friends."},
    {'title': 'Climbing the outdoor frame',
     'content': "{name} approached the climbing frame with real determination today, testing each "
                "foothold before shifting weight onto it. Halfway up {name} paused, worked out a "
                "different route, and carried on to the top - then called out for a teacher to watch "
                "the climb back down."},
    {'title': 'Caring for the garden',
     'content': "{name} helped water the vegetable garden this afternoon, filling the small watering "
                "can and carrying it carefully to each row. {name} noticed one of the seedlings had "
                "fallen over and asked whether we could prop it back up, then found a stick to help."},
    {'title': 'Building with blocks',
     'content': "{name} worked on a long block construction that stretched across the mat, testing "
                "which shapes would balance on top of others. When one section collapsed, {name} "
                "rebuilt it with a wider base and explained to a friend that the big ones go on "
                "the bottom."},
    {'title': 'Music and movement',
     'content': "{name} joined in enthusiastically with the shakers today, keeping time with the beat "
                "and adding their own movements between verses. {name} then led a small group in "
                "making up new actions for the final chorus."},
    {'title': 'Water play discoveries',
     'content': "At the water trough {name} spent a long time experimenting with which objects floated "
                "and which sank, lining them up on the edge in two groups. {name} was surprised when "
                "the large plastic lid floated and tested it several more times to be sure."},
]


def fetch_param_values(cur, param_type):
    """Reads a list of active param_value strings from the Params table.
    These rows are inserted by populate_database.sql, which must be run
    before this script."""
    cur.execute(
        "SELECT param_value FROM Params WHERE param_type = %s AND status = 'Active' ORDER BY id;",
        (param_type,)
    )
    values = [row['param_value'] for row in cur.fetchall()]
    if not values:
        raise RuntimeError(
            f"No Params rows found for param_type='{param_type}'. "
            f"Did you run populate_database.sql before this script?"
        )
    return values


def dob_for_classroom(classroom_index):
    """Roughly: Piwakawaka (0-2yrs), Kereru (2-3yrs), Tui (3-5yrs)."""
    ranges = [(0.5, 2), (2, 3), (3, 5)]
    min_y, max_y = ranges[classroom_index]
    years = random.uniform(min_y, max_y)
    return date.today() - timedelta(days=round(years * 365))


def main():
    print('Hashing shared seed password...')
    password_hash = flask_bcrypt.generate_password_hash(SEED_PASSWORD).decode('utf-8')

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        print('Reading classrooms and curriculum strands from Params...')
        classrooms = fetch_param_values(cur, 'classroom')
        strands_pool = fetch_param_values(cur, 'curriculum_strand')
        outcomes_pool = fetch_param_values(cur, 'learning_outcome')
        print(f'  {len(classrooms)} classrooms, {len(strands_pool)} strands, {len(outcomes_pool)} outcomes')

        cur.execute("SELECT centre_id FROM Centres ORDER BY centre_id LIMIT 1;")
        centre_row = cur.fetchone()
        if not centre_row:
            raise RuntimeError(
                "No rows found in Centres. Did you run populate_database.sql before this script?"
            )
        centre_id = centre_row['centre_id']
        print(f'  Using centre_id={centre_id}')

        if len(TEACHER_NAMES) != len(classrooms) * 2:
            raise RuntimeError(
                f'Expected {len(classrooms) * 2} teacher names (2 per classroom) '
                f'to match the {len(classrooms)} classrooms in Params, '
                f'but TEACHER_NAMES has {len(TEACHER_NAMES)}. '
                f'Update TEACHER_NAMES or populate_database.sql to match.'
            )

        print('Clearing existing accounts and demo content (Params is left untouched)...')
        cur.execute("""
            TRUNCATE TABLE Notifications, Accident_Forms, Messages, Attendance,
                Learning_Stories, Parent_Child, Children, Users
                RESTART IDENTITY CASCADE
        """)

        # --- 1 super admin ---------------------------------------------
        cur.execute(
            """INSERT INTO Users (role, full_name, email, password_hash, phone, centre_id, status)
               VALUES ('Admin', 'Whariki Connect Admin', 'admin@sunnypreschool.nz', %s, '021 000 0001', %s, 'approved')
               RETURNING user_id""",
            (password_hash, centre_id)
        )
        print(f"Created admin user (id={cur.fetchone()['user_id']})")

        # --- 6 teachers, 2 per classroom --------------------------------
        teacher_ids = []
        for i, name in enumerate(TEACHER_NAMES):
            classroom = classrooms[i // 2]
            email = name.lower().replace(' ', '.').replace("'", '') + '@sunnypreschool.nz'
            cur.execute(
                """INSERT INTO Users (role, full_name, email, password_hash, phone, classroom, centre_id, status)
                   VALUES ('Teacher', %s, %s, %s, %s, %s, %s, 'approved') RETURNING user_id""",
                (name, email, password_hash, f'021 000 01{i:02d}', classroom, centre_id)
            )
            teacher_ids.append(cur.fetchone()['user_id'])
        print(f'Created {len(teacher_ids)} teacher accounts')

        # --- 20 children + 40 parents (2 parents per child) -------------
        child_ids = []
        parent_count = 0

        for i, (first_name, last_name) in enumerate(CHILDREN):
            classroom_index = min(i // 7, 2)
            classroom = classrooms[classroom_index]
            dob = dob_for_classroom(classroom_index)

            parent_a = PARENT_FIRST_NAMES[(i * 2) % len(PARENT_FIRST_NAMES)]
            parent_b = PARENT_FIRST_NAMES[(i * 2 + 1) % len(PARENT_FIRST_NAMES)]
            emergency_contact = f'{parent_a} {last_name}'
            emergency_phone = f'022 {100 + i:03d} {1000 + i}'

            cur.execute(
                """INSERT INTO Children (first_name, last_name, date_of_birth, classroom,
                                          emergency_contact, emergency_phone)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING child_id""",
                (first_name, last_name, dob, classroom, emergency_contact, emergency_phone)
            )
            child_id = cur.fetchone()['child_id']
            child_ids.append({'id': child_id, 'classroom': classroom})

            for idx, parent_first in enumerate([parent_a, parent_b]):
                parent_count += 1
                relationship = 'mother' if idx == 0 else 'father'
                email = f'{parent_first.lower()}.{last_name.lower()}{i}@example.co.nz'
                phone = f'027 {200 + parent_count:03d} {2000 + parent_count}'
                cur.execute(
                    """INSERT INTO Users (role, full_name, email, password_hash, phone, centre_id, status)
                       VALUES ('Parent', %s, %s, %s, %s, %s, 'approved') RETURNING user_id""",
                    (f'{parent_first} {last_name}', email, password_hash, phone, centre_id)
                )
                parent_id = cur.fetchone()['user_id']
                cur.execute(
                    """INSERT INTO Parent_Child (parent_id, child_id, relationship)
                       VALUES (%s, %s, %s)""",
                    (parent_id, child_id, relationship)
                )
        print(f'Created {len(child_ids)} children and {parent_count} parent accounts')

        # --- demo content: today's attendance + a few learning stories --
        today = date.today()
        for i, child in enumerate(child_ids):
            room_teacher_ids = teacher_ids[classrooms.index(child['classroom']) * 2:
                                            classrooms.index(child['classroom']) * 2 + 2]
            teacher_id = room_teacher_ids[i % 2]

            cur.execute(
                """INSERT INTO Attendance (child_id, date, check_in_time, status, recorded_by)
                   VALUES (%s, %s, now() - interval '2 hours', 'present', %s)""",
                (child['id'], today, teacher_id)
            )

            # Two learning stories per child, drawn from the templates above
            # so every child has a populated portfolio to look at.
            first_name = [c for c in CHILDREN][i][0]
            for offset in (0, 1):
                template = STORY_TEMPLATES[(i * 2 + offset) % len(STORY_TEMPLATES)]
                story_strands = [strands_pool[(i + offset) % len(strands_pool)],
                                 strands_pool[(i + offset + 2) % len(strands_pool)]]
                story_outcomes = [
                    outcomes_pool[(i * 2 + offset) % len(outcomes_pool)],
                    outcomes_pool[(i * 2 + offset + 5) % len(outcomes_pool)],
                ]
                cur.execute(
                    """INSERT INTO Learning_Stories
                         (child_id, teacher_id, title, content, strands, outcomes, status, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, 'published', now() - (%s || ' days')::interval)""",
                    (
                        child['id'], teacher_id,
                        template['title'],
                        template['content'].format(name=first_name),
                        story_strands, story_outcomes,
                        offset * 7 + 2,
                    )
                )

        # --- one sample accident form, to demonstrate the workflow -------
        first_teacher = teacher_ids[0]
        first_child = child_ids[0]['id']
        cur.execute(
            """INSERT INTO Accident_Forms
                (child_id, teacher_id, incident_date, incident_time, location,
                 nature_of_injury, body_part, description, action_taken,
                 parent_contacted, parent_contacted_name, contacted_by, contact_method,
                 parent_contacted_time, medical_attention_needed, notifiable_event,
                 status, provider_signature, teacher_signed_at)
               VALUES (%s, %s, CURRENT_DATE - 1, '10:35', 'Outdoor playground',
                       'Graze / scrape', 'Knee', %s, %s,
                       true, %s, %s, 'Phone', '10:50', false, false,
                       'submitted', %s, now())""",
            (first_child, first_teacher,
             'Child fell while running on the playground and grazed their knee on the concrete.',
             'Cleaned the graze with water, applied a plaster, and comforted the child. '
             'Continued to monitor for the rest of the day.',
             'Emma Smith', TEACHER_NAMES[0], TEACHER_NAMES[0])
        )

        conn.commit()
        print('\nSeed complete.')
        print(f'All accounts share the password: {SEED_PASSWORD}')
        print('Example logins:')
        print('  admin@sunnypreschool.nz          (Admin)')
        print('  sarah.thompson@sunnypreschool.nz (Teacher)')
        print('  (see the Users table for the full list of parent emails)')

    except Exception as err:
        conn.rollback()
        print(f'Seed failed, rolled back: {err}')
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
