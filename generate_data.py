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
from datetime import date, datetime, time, timedelta

import psycopg2
import psycopg2.extras
from flask import Flask
from flask_bcrypt import Bcrypt


def weighted_choice(pairs):
    """pairs is a list of (value, weight) tuples. Used throughout this script
    for any 'mostly X, sometimes Y' distribution - attendance status, meal
    outcomes, etc - so those distributions read the same way everywhere."""
    total = sum(w for _, w in pairs)
    roll = random.uniform(0, total)
    upto = 0
    for value, weight in pairs:
        upto += weight
        if roll <= upto:
            return value
    return pairs[-1][0]

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

# ---------------------------------------------------------------------------
# Health & safety, dietary requirements, and immunisation seed data.
# Roughly matches real-world prevalence for an ECE setting - most children
# have nothing recorded here, which is itself realistic.
# ---------------------------------------------------------------------------
ALLERGY_POOL = [
    'Peanuts - anaphylaxis risk, EpiPen kept in bag (see instructions inside lid)',
    'Tree nuts (cashew, almond)',
    'Dairy / lactose intolerance',
    'Egg',
    'Bee and wasp stings - carries antihistamine',
    'Penicillin',
    'Shellfish',
    'Kiwifruit',
    'Sesame',
    'Strawberries - mild, causes a rash',
]
MEDICAL_CONDITION_POOL = [
    'Asthma - reliever inhaler in bag, use if wheezing or persistent coughing',
    'Eczema - apply own cream after water play and before sleep',
    'Grommets fitted - avoid submerging ears during water play',
    'Mild hearing loss in left ear - seat towards the front at mat time',
    'Febrile seizure history - notify parents immediately for any fever over 38°C',
]
MEDICATION_POOL = [
    'Ventolin inhaler as needed for asthma (asthma plan on file)',
    'Antihistamine given at home each morning during spring',
    'Eczema cream applied twice daily',
    'Paracetamol only with prior parent phone permission',
]
DIETARY_POOL = [
    'Vegetarian', 'Dairy-free (lactose intolerant)', 'Gluten-free (coeliac)',
    'Halal', 'No pork (family preference)', 'Vegan',
]
GP_NAMES = [
    'Dr. Sarah Lim', 'Dr. Michael O\u2019Brien', 'Dr. Priya Anand', 'Dr. James Wu',
    'Dr. Hana Ngata', 'Dr. Robert Singh',
]
GP_CLINICS = [
    'Eastside Medical Centre', 'Riverside Family Practice', 'Harbourview GP',
    'Central Health Clinic', 'Sunnydale Medical',
]

# NZ National Immunisation Schedule, simplified to the multi-antigen
# combinations actually given. (due_age_months, [(vaccine, dose_label), ...])
IMMUNISATION_SCHEDULE = [
    (1.5, [('Rotavirus', '1st dose'),
           ('DTaP-IPV-Hib-HepB (6-in-1)', '1st dose'),
           ('PCV13 (Pneumococcal)', '1st dose')]),
    (3, [('Rotavirus', '2nd dose'),
         ('DTaP-IPV-Hib-HepB (6-in-1)', '2nd dose'),
         ('PCV13 (Pneumococcal)', '2nd dose')]),
    (5, [('DTaP-IPV-Hib-HepB (6-in-1)', '3rd dose'),
         ('PCV13 (Pneumococcal)', '3rd dose')]),
    (12, [('MMR (Measles, Mumps, Rubella)', '1st dose'),
          ('PCV13 (Pneumococcal)', 'Booster')]),
    (15, [('Hib booster', 'Booster'),
          ('Varicella (Chickenpox)', '1st dose')]),
    (48, [('DTaP-IPV (4-in-1 booster)', 'Booster'),
          ('MMR (Measles, Mumps, Rubella)', '2nd dose')]),
]


def generate_health_info(rng):
    """Returns (allergies, medical_conditions, medications, dietary, notes)
    for one child - mostly None, since most children have nothing on file."""
    has_allergy = rng.random() < 0.25
    has_condition = rng.random() < 0.15
    has_dietary = rng.random() < 0.20

    allergies = None
    if has_allergy:
        picks = rng.sample(ALLERGY_POOL, 2 if rng.random() < 0.15 else 1)
        allergies = '; '.join(picks)

    medical_conditions = rng.choice(MEDICAL_CONDITION_POOL) if has_condition else None
    medications = None
    if has_condition and rng.random() < 0.65:
        medications = rng.choice(MEDICATION_POOL)
    elif rng.random() < 0.05:
        medications = rng.choice(MEDICATION_POOL)

    dietary_requirements = rng.choice(DIETARY_POOL) if has_dietary else None

    medical_notes = None
    if has_allergy or has_condition:
        gp = rng.choice(GP_NAMES)
        clinic = rng.choice(GP_CLINICS)
        phone = f'03 {rng.randint(300, 599)} {rng.randint(1000, 9999)}'
        medical_notes = f'GP: {gp}, {clinic}, {phone}.'
        if has_allergy and rng.random() < 0.3:
            medical_notes += ' Please call parents immediately for any suspected reaction, even mild.'

    return allergies, medical_conditions, medications, dietary_requirements, medical_notes


def generate_immunizations(rng, dob, today):
    """Realistic-looking status per NZ schedule milestone, based on age."""
    age_months = (today - dob).days / 30.44
    records = []
    exempt_family = rng.random() < 0.03  # a small share of families opt out entirely

    for due_age, vaccines in IMMUNISATION_SCHEDULE:
        if due_age > age_months + 2:
            continue  # not yet relevant, don't clutter the record
        for vaccine_name, dose_label in vaccines:
            if exempt_family:
                records.append((vaccine_name, dose_label, None, 'exempt',
                                 'Parental exemption on file.'))
                continue
            if due_age > age_months:
                records.append((vaccine_name, dose_label, None, 'scheduled', None))
                continue
            roll = rng.random()
            if roll < 0.88:
                given_days = due_age * 30.44 + rng.randint(-5, 25)
                given_date = min(dob + timedelta(days=round(given_days)), today)
                records.append((vaccine_name, dose_label, given_date, 'completed', None))
            elif roll < 0.96:
                records.append((vaccine_name, dose_label, None, 'overdue', None))
            else:
                records.append((vaccine_name, dose_label, None, 'exempt',
                                 'Parental exemption on file.'))

    # Annual flu vaccine - not on the core schedule, uptake is partial.
    if age_months >= 6 and not exempt_family and rng.random() < 0.55:
        flu_date = date(today.year, 4, rng.randint(1, 28))
        if flu_date <= today:
            records.append(('Influenza (annual)', 'Annual', flu_date, 'completed', None))

    return records


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
        CLASSROOMS_ORDER = list(classrooms)
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
            allergies, medical_conditions, medications, dietary_requirements, medical_notes = \
                generate_health_info(random)

            cur.execute(
                """INSERT INTO Children (first_name, last_name, date_of_birth, classroom,
                                          emergency_contact, emergency_phone,
                                          allergies, medical_conditions, medications,
                                          dietary_requirements, medical_notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING child_id""",
                (first_name, last_name, dob, classroom, emergency_contact, emergency_phone,
                 allergies, medical_conditions, medications, dietary_requirements, medical_notes)
            )
            child_id = cur.fetchone()['child_id']
            child_ids.append({'id': child_id, 'classroom': classroom, 'dob': dob})

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

        today = date.today()

        # --- attendance history: 3 months up to today -----------------------
        # Weekdays only, present most of the time with occasional absence/
        # sick/leave days, so Attendance trend charts have something real to
        # show rather than a single "checked in today" row.
        print('Generating 3 months of attendance history...')
        ATTENDANCE_START = today - timedelta(days=92)  # ~3 calendar months back
        ATTENDANCE_WEIGHTS = [('present', 88), ('absent', 5), ('sick', 5), ('on_leave', 2)]
        attendance_rows = 0

        for i, child in enumerate(child_ids):
            room_teacher_ids = teacher_ids[classrooms.index(child['classroom']) * 2:
                                            classrooms.index(child['classroom']) * 2 + 2]

            day_count = (today - ATTENDANCE_START).days
            for day_offset in range(day_count + 1):
                current = ATTENDANCE_START + timedelta(days=day_offset)
                if current.weekday() >= 5:          # centre closed weekends
                    continue
                if current > today:
                    continue

                status = weighted_choice(ATTENDANCE_WEIGHTS)
                teacher_id = room_teacher_ids[day_offset % 2]
                check_in = check_out = None

                if status == 'present':
                    arrive_minute = random.randint(-20, 25)
                    check_in = datetime.combine(current, time(8, 30)) + timedelta(minutes=arrive_minute)
                    # Today's child may still be at the centre - only some
                    # already-checked-in-today rows have a checkout time.
                    if current < today or random.random() < 0.4:
                        leave_minute = random.randint(-20, 30)
                        check_out = datetime.combine(current, time(15, 30)) + timedelta(minutes=leave_minute)

                cur.execute(
                    """INSERT INTO Attendance (child_id, date, check_in_time, check_out_time, status, recorded_by)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (child_id, date) DO NOTHING""",
                    (child['id'], current, check_in, check_out, status, teacher_id)
                )
                attendance_rows += 1
        print(f'  {attendance_rows} attendance records created ({ATTENDANCE_START} to {today})')

        # --- two learning stories per child, so every portfolio is populated ---
        for i, child in enumerate(child_ids):
            room_teacher_ids = teacher_ids[classrooms.index(child['classroom']) * 2:
                                            classrooms.index(child['classroom']) * 2 + 2]
            teacher_id = room_teacher_ids[i % 2]

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

        # --- daily routine records: 3 months, matching the Attendance window ---
        # Meals and toileting for every child on weekdays, with realistic
        # times and outcomes. Younger rooms are in nappies; the preschool
        # room mostly uses the toilet independently.
        print('Generating routine records (3 months)...')

        MEAL_SLOTS = [
            ('Morning tea', time(9, 30), 20),    # (name, base time, +/- minutes)
            ('Lunch', time(12, 0), 25),
            ('Afternoon tea', time(14, 45), 20),
        ]
        # Most children eat well; "None" is rare, as it would be in practice.
        MEAL_OUTCOME_WEIGHTS = [('All', 45), ('Most', 33), ('Some', 18), ('None', 4)]

        # A handful of children go through a rough patch for a few weeks (more
        # "Some"/"None" meals, more toileting accidents) so the trend chart
        # actually has something worth noticing, not a flat line all term.
        rough_patch_children = set(random.sample(range(len(child_ids)), k=4))

        routine_rows = 0
        start_day = ATTENDANCE_START  # reuse the same ~3-month window

        for i, child in enumerate(child_ids):
            classroom_index = CLASSROOMS_ORDER.index(child['classroom'])
            # Piwakawaka (0) and Kereru (1) are nappies; Tui (2) is toilet-trained.
            in_nappies = classroom_index < 2
            room_teacher_ids = teacher_ids[classroom_index * 2: classroom_index * 2 + 2]

            # A 2-3 week rough patch somewhere in the middle of the term.
            has_rough_patch = i in rough_patch_children
            rough_start = random.randint(25, 55) if has_rough_patch else None
            rough_len = random.randint(12, 20) if has_rough_patch else 0

            day_count = (today - start_day).days
            for day_offset in range(day_count + 1):
                current = start_day + timedelta(days=day_offset)
                if current.weekday() >= 5:      # centre closed at the weekend
                    continue
                if current > today:
                    continue
                # Children are not at the centre every single day.
                if random.random() < 0.12:
                    continue

                in_rough_patch = has_rough_patch and rough_start <= day_offset < rough_start + rough_len
                teacher_id = room_teacher_ids[day_offset % 2]

                # --- meals ---
                for meal_name, base_time, jitter in MEAL_SLOTS:
                    # Afternoon tea is sometimes missed by early pick-ups.
                    if meal_name == 'Afternoon tea' and random.random() < 0.2:
                        continue
                    minute_shift = random.randint(-jitter, jitter)
                    at = (datetime.combine(current, base_time)
                          + timedelta(minutes=minute_shift))
                    meal_weights = ([('All', 15), ('Most', 25), ('Some', 35), ('None', 25)]
                                    if in_rough_patch else MEAL_OUTCOME_WEIGHTS)
                    outcome = weighted_choice(meal_weights)
                    note = None
                    if outcome == 'None' and random.random() < 0.6:
                        note = random.choice([
                            'Not hungry today', 'Was tired', 'Wanted to keep playing'])
                    elif outcome == 'All' and random.random() < 0.12:
                        note = 'Asked for seconds'
                    cur.execute(
                        """INSERT INTO Routines
                             (child_id, recorded_by, date, category, routine_type,
                              outcome, recorded_at, notes)
                           VALUES (%s, %s, %s, 'meal', %s, %s, %s, %s)""",
                        (child['id'], teacher_id, current, meal_name, outcome, at, note)
                    )
                    routine_rows += 1

                # --- toileting ---
                if in_nappies:
                    # Nappies changed roughly every couple of hours.
                    for base_hour in (9, 11, 13, 15):
                        if random.random() < 0.12:
                            continue
                        at = (datetime.combine(current, time(base_hour, 0))
                              + timedelta(minutes=random.randint(0, 45)))
                        nappy_weights = ([('Wet', 40), ('Soiled', 45), ('Dry', 15)]
                                         if in_rough_patch else [('Wet', 60), ('Soiled', 22), ('Dry', 18)])
                        outcome = weighted_choice(nappy_weights)
                        cur.execute(
                            """INSERT INTO Routines
                                 (child_id, recorded_by, date, category, routine_type,
                                  outcome, recorded_at, notes)
                               VALUES (%s, %s, %s, 'toileting', 'Nappy change', %s, %s, %s)""",
                            (child['id'], teacher_id, current, outcome, at,
                             'Cream applied' if outcome == 'Soiled' and random.random() < 0.25 else None)
                        )
                        routine_rows += 1
                else:
                    for base_hour in (9, 11, 13, 15):
                        if random.random() < 0.18:
                            continue
                        at = (datetime.combine(current, time(base_hour, 0))
                              + timedelta(minutes=random.randint(0, 45)))
                        # Occasional accidents are normal at this age; more
                        # frequent during a child's rough patch.
                        accident_chance = 0.28 if in_rough_patch else 0.08
                        outcome = 'Accident' if random.random() < accident_chance else 'Success'
                        cur.execute(
                            """INSERT INTO Routines
                                 (child_id, recorded_by, date, category, routine_type,
                                  outcome, recorded_at, notes)
                               VALUES (%s, %s, %s, 'toileting', 'Toilet', %s, %s, %s)""",
                            (child['id'], teacher_id, current, outcome, at,
                             'Change of clothes needed' if outcome == 'Accident' else None)
                        )
                        routine_rows += 1

        print(f'  {routine_rows} routine records created')

        # --- immunisation records, per the NZ National Immunisation Schedule ---
        print('Generating immunisation records...')
        today = date.today()
        immunization_rows = 0
        for i, child in enumerate(child_ids):
            classroom_index = CLASSROOMS_ORDER.index(child['classroom'])
            room_teacher_ids = teacher_ids[classroom_index * 2: classroom_index * 2 + 2]
            teacher_id = room_teacher_ids[i % 2]

            for vaccine_name, dose_label, date_given, status, notes in \
                    generate_immunizations(random, child['dob'], today):
                cur.execute(
                    """INSERT INTO Immunizations
                         (child_id, recorded_by, vaccine_name, dose_label, date_given, status, notes)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (child['id'], teacher_id, vaccine_name, dose_label, date_given, status, notes)
                )
                immunization_rows += 1
        print(f'  {immunization_rows} immunisation records created')

        # --- accident forms: spread realistically over the last 3 months ----
        # Not a daily occurrence - most days have none. ~20 accidents across
        # 20 children over ~90 days is roughly one every 4-5 days centre-wide,
        # which is a believable rate for a small ECE service.
        print('Generating accident forms (last 3 months)...')

        LOCATIONS = [
            'Outdoor playground', 'Sandpit', 'Indoor mat area', 'Bathroom',
            'Climbing frame', 'Bike track', 'Water play area', 'Dress-up corner',
        ]
        # (nature, body_part, weight, needs_medical, notifiable)
        INJURY_PROFILES = [
            ('Graze / scrape', 'Knee', 30, False, False),
            ('Graze / scrape', 'Hand / fingers', 15, False, False),
            ('Bruise', 'Leg', 15, False, False),
            ('Bruise', 'Arm', 10, False, False),
            ('Bump to the head', 'Head', 12, False, False),
            ('Cut / laceration', 'Hand / fingers', 8, True, False),
            ('Bite', 'Arm', 5, False, False),
            ('Sprain / strain', 'Foot / toes', 3, True, False),
            ('Burn / scald', 'Hand / fingers', 1, True, True),
        ]
        DESCRIPTIONS = {
            'Graze / scrape': 'Tripped and grazed themselves while running/playing outdoors.',
            'Bruise': 'Bumped into equipment while playing and was left with a bruise.',
            'Bump to the head': 'Lost balance and bumped their head on a low shelf/piece of equipment.',
            'Cut / laceration': 'Caught their hand on the edge of a piece of equipment.',
            'Bite': 'Was bitten by another child during a dispute over a toy.',
            'Sprain / strain': 'Twisted their ankle jumping off the low step on the climbing frame.',
            'Burn / scald': 'Touched a hot surface briefly before being stopped by a teacher.',
        }
        ACTIONS = {
            'Graze / scrape': 'Cleaned with water, applied a plaster, and comforted the child.',
            'Bruise': 'Applied a cold pack and comforted the child; monitored for the rest of the day.',
            'Bump to the head': 'Applied a cold pack, monitored closely for the next hour for any signs of concussion.',
            'Cut / laceration': 'Cleaned the wound, applied a dressing, and monitored throughout the day.',
            'Bite': 'Cleaned the area with water and applied a cold pack; spoke with both children involved.',
            'Sprain / strain': 'Applied ice, elevated the foot, and limited weight-bearing activity for the rest of the day.',
            'Burn / scald': 'Ran the area under cool water for several minutes and applied a dressing.',
        }

        teacher_names_by_id = dict(zip(teacher_ids, TEACHER_NAMES))

        accident_dates = sorted(random.sample(
            range((today - timedelta(days=90) - date(2000, 1, 1)).days,
                  (today - date(2000, 1, 1)).days),
            k=20
        ))

        def parent_name_for_child(child_id):
            cur.execute(
                """SELECT u.full_name FROM Users u
                   JOIN Parent_Child pc ON pc.parent_id = u.user_id
                   WHERE pc.child_id = %s ORDER BY u.user_id LIMIT 1;""",
                (child_id,)
            )
            row = cur.fetchone()
            return row['full_name'] if row else None

        accident_rows = 0
        for day_number in accident_dates:
            incident_date = date(2000, 1, 1) + timedelta(days=day_number)
            if incident_date.weekday() >= 5:
                continue  # closed weekends - no accidents to record

            child = random.choice(child_ids)
            classroom_index = CLASSROOMS_ORDER.index(child['classroom'])
            teacher_id = teacher_ids[classroom_index * 2 + random.randint(0, 1)]

            nature, body_part, _, needs_medical, notifiable = random.choices(
                INJURY_PROFILES, weights=[p[2] for p in INJURY_PROFILES], k=1
            )[0]

            incident_time = time(random.randint(9, 15), random.choice([0, 15, 30, 45]))
            contact_time = time(incident_time.hour, min(incident_time.minute + 15, 59))

            cur.execute(
                """INSERT INTO Accident_Forms
                    (child_id, teacher_id, incident_date, incident_time, location,
                     nature_of_injury, body_part, description, action_taken,
                     parent_contacted, parent_contacted_name, contacted_by, contact_method,
                     parent_contacted_time, medical_attention_needed, notifiable_event,
                     status, provider_signature, teacher_signed_at)
                   VALUES (%s, %s, %s, %s, %s,
                           %s, %s, %s, %s,
                           true, %s, %s, 'Phone',
                           %s, %s, %s,
                           'submitted', %s, %s)""",
                (child['id'], teacher_id, incident_date, incident_time,
                 random.choice(LOCATIONS),
                 nature, body_part, DESCRIPTIONS[nature], ACTIONS[nature],
                 parent_name_for_child(child['id']), teacher_names_by_id[teacher_id], contact_time,
                 needs_medical, notifiable,
                 teacher_names_by_id[teacher_id],
                 datetime.combine(incident_date, incident_time))
            )
            accident_rows += 1
        print(f'  {accident_rows} accident forms created')


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
