"""
Backfill health & safety info + immunisation records for EXISTING children.
=============================================================================
Unlike generate_data.py, this script does NOT truncate anything - it's safe
to run on a database you've already been using (messages, attendance
history, etc. are left untouched).

What it does, for every row in Children:
  - If allergies/medical_conditions/medications/dietary_requirements/
    medical_notes are all still empty, fills them in with realistic (mostly
    "nothing to report") demo data.
  - If the child has zero rows in Immunizations, generates a realistic set
    based on the NZ National Immunisation Schedule and their date of birth.

Already-edited children (i.e. anyone who has since typed real allergy info,
or already has immunisation records) are left completely alone - safe to
re-run at any time.

Requires migrate_health_and_announcements.sql to have been run first (or a
fresh create_database.sql), since it needs the new columns/tables to exist.

Usage:
    python seed_medical_immunization_data.py
"""
from datetime import date

import psycopg2
import psycopg2.extras

from app.db import connect
from generate_data import generate_health_info, generate_immunizations
import random

DB_CONFIG = {
    "host": connect.dbhost,
    "port": connect.dbport,
    "dbname": connect.dbname,
    "user": connect.dbuser,
    "password": connect.dbpass,
}


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    today = date.today()

    try:
        cur.execute(
            """SELECT child_id, first_name, last_name, date_of_birth, classroom
               FROM Children
               WHERE allergies IS NULL AND medical_conditions IS NULL
                 AND medications IS NULL AND dietary_requirements IS NULL
                 AND medical_notes IS NULL;"""
        )
        children_needing_health = cur.fetchall()

        health_updated = 0
        for child in children_needing_health:
            allergies, conditions, meds, dietary, notes = generate_health_info(random)
            cur.execute(
                """UPDATE Children
                   SET allergies = %s, medical_conditions = %s, medications = %s,
                       dietary_requirements = %s, medical_notes = %s
                   WHERE child_id = %s;""",
                (allergies, conditions, meds, dietary, notes, child["child_id"])
            )
            health_updated += 1
        print(f"Health & safety info filled in for {health_updated} child(ren) "
              f"(skipped any that already had something recorded).")

        cur.execute(
            """SELECT c.child_id, c.date_of_birth, c.classroom
               FROM Children c
               LEFT JOIN Immunizations i ON i.child_id = c.child_id
               WHERE i.immunization_id IS NULL;"""
        )
        children_needing_immunizations = cur.fetchall()

        # Prefer a teacher in the child's own classroom as recorded_by, same
        # as generate_data.py does; fall back to any teacher if the room has
        # none (e.g. a hand-created child not tied to a seeded teacher).
        cur.execute("SELECT user_id, classroom FROM Users WHERE role = 'Teacher';")
        teachers_by_classroom = {}
        any_teacher_id = None
        for row in cur.fetchall():
            teachers_by_classroom.setdefault(row["classroom"], []).append(row["user_id"])
            any_teacher_id = row["user_id"]

        immunization_rows = 0
        children_with_immunizations = 0
        for child in children_needing_immunizations:
            room_teachers = teachers_by_classroom.get(child["classroom"]) or (
                [any_teacher_id] if any_teacher_id else [])
            if not room_teachers:
                continue  # no teacher accounts at all yet - nothing to attribute records to
            teacher_id = random.choice(room_teachers)

            records = generate_immunizations(random, child["date_of_birth"], today)
            for vaccine_name, dose_label, date_given, status, notes in records:
                cur.execute(
                    """INSERT INTO Immunizations
                         (child_id, recorded_by, vaccine_name, dose_label, date_given, status, notes)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (child["child_id"], teacher_id, vaccine_name, dose_label, date_given, status, notes)
                )
                immunization_rows += 1
            if records:
                children_with_immunizations += 1

        print(f"Immunisation records created for {children_with_immunizations} child(ren) "
              f"({immunization_rows} records total; skipped any child who already had records).")

        conn.commit()
        print("\nDone. No existing data was deleted or overwritten.")

    except Exception as err:
        conn.rollback()
        print(f"Backfill failed, rolled back: {err}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
