# Whāriki Connect (Flask / Python edition)

A unified web platform for New Zealand Early Childhood Education (ECE)
centres. Brings **learning stories**, **parent–teacher messaging**, **daily
attendance**, and **accident/incident forms** into one login, so teachers
don't have to switch between three or four separate apps to manage one
classroom.

Built for a COMP693 web development project, following the same
Flask + PostgreSQL + raw SQL architecture as the Tuatara/ConservaTrack
project.

## Tech stack

- **Backend:** Python 3 + Flask (server-rendered Jinja2 templates, session-based auth)
- **Database:** PostgreSQL via `psycopg2`, raw SQL (no ORM) — same connection-pool
  pattern (`app/db/db.py`) as the Tuatara project
- **Passwords:** hashed with `Flask-Bcrypt` before being stored
- **Frontend:** plain HTML/CSS via Jinja2 templates — no JS build step

## Project structure

```
whariki-connect-py/
├── app/
│   ├── __init__.py            # Flask app setup, registers route modules
│   ├── db/
│   │   ├── db.py              # PostgreSQL connection pool
│   │   └── connect.py         # your local DB credentials (gitignored)
│   ├── utils.py                # password hashing, login/role decorators, get_cursor()
│   ├── models.py                # dataclasses documenting the main entities
│   ├── common_routes.py         # home, login, logout, overview dashboard
│   ├── child_routes.py          # children list + aggregated child profile
│   ├── learning_story_routes.py
│   ├── attendance_routes.py
│   ├── message_routes.py
│   ├── accident_routes.py
│   ├── notification_routes.py
│   ├── admin_routes.py
│   ├── repository/              # one file per feature area - all raw SQL
│   ├── templates/                # Jinja2 templates
│   └── static/
│       ├── css/style.css
│       └── img/           # logo mark (SVG) + generated favicons
├── create_database.sql          # schema
├── populate_database.sql        # static lookup data (classrooms, curriculum strands, etc.)
├── clear_database.sql           # wipes data for re-seeding
├── generate_data.py              # seeds accounts + demo content (needs bcrypt, so it's Python not SQL)
├── password_hash_generator.py    # standalone bcrypt hash/verify check
├── requirements.txt
├── run.py                        # entry point
└── .vscode/settings.json
```

## Features

| Module | What it does |
|---|---|
| Auth & roles | Parent / Teacher / Admin accounts, session-based login, role-based access control enforced server-side |
| Child profile | One page per child aggregating learning stories, attendance and accident history |
| AI writing assistant | Optional Q&A helper in the learning story editor. Uses **Groq** by default (free tier, no credit card — get a key at console.groq.com/keys and set `GROQ_API_KEY`). Google Gemini is supported as an alternative via `AI_PROVIDER=gemini`. Visit `/ai-status` to check the setup and run a live test |
| Learning stories | Teachers post observations tagged to *Te Whāriki* curriculum strands; parents view them |
| Attendance | Teachers check children in/out; parents view attendance history |
| Messaging | Parent–teacher chat scoped to a child, with message notifications |
| Accident forms | Teachers file incident reports (with a "notifiable event" flag per NZ H&S law); linked parents must acknowledge them |
| Notifications | In-app feed for new stories, messages, and accident forms |
| Admin panel | Centre-wide stats and a staff/family directory |
| Learning stories | Dedicated `/learning-stories` page. Teachers write observations tagged against all 5 Te Whāriki strands **and all 20 learning outcomes**, with photo upload and save-as-draft. Parents see published stories for their own children; teachers see everything they've written and which child it's about |
| Attendance | Dedicated `/attendance` page. Parents check their child in/out each day; teachers get a month calendar and can correct or back-date any day |
| Accident forms | Dedicated `/accidents` page laid out like the paper accident report (incident details, caregiver response, parent-contact block, signature). Teachers only; save as draft or submit. Parents view and acknowledge submitted forms for their own children |
| Profiles | Every user can update their own name, phone and profile photo at `/profile`. Parents can also update each of their children's emergency contact details and photo. No photo falls back to the initials avatar |
| Daily routines | Teachers record meals (morning tea, lunch, afternoon tea) and toileting (nappy changes / independent toilet use) on each child's profile. Parents see their own children's records only |
| Analytics dashboard | R/ggplot2 charts at `/analytics` (Teacher/Admin only) generated from the app's own data. Four charts: strand coverage, weekly attendance rate, accident frequency, and per-child routine trends (meal/toileting). Every chart is collapsible, has its own date-range filter, and can be downloaded as a PNG, scoped to the teacher's room or centre-wide for admin. Requires R + ggplot2 installed locally (`RSCRIPT_PATH` env var if Rscript isn't on PATH) — degrades to a clear setup message rather than crashing if not installed |
| Timesheet | Teachers fill in and edit their own weekly hours at `/timesheet`; admin views/edits any teacher's timesheet and approves a week (locking it against further teacher edits) at `/timesheet/admin`, with a monthly all-teacher hours summary |
| Add a child (Admin) | `/children/new` — Admin registers a brand-new child directly: name, DOB, classroom, emergency contact, health & safety info, optional photo, and optional linking to one or more already-approved parent accounts in the same step |
| Account management (Admin) | `/admin/users/<id>` — deactivate/reactivate an approved account, reassign a teacher's classroom, and trigger a password reset link on a user's behalf (emails it if SMTP is configured, otherwise shows the link to the admin). Linked from each row of the Staff & families table on the admin dashboard |
| Edit a child's basic info (Admin) | `/children/<id>/edit` — fix a child's name, date of birth or classroom after creation, previously only settable once at creation time |
| Child withdrawal (Admin) | Mark a child as withdrawn from the child profile page — never a hard delete, all history (learning stories, attendance, etc.) is kept, just hidden from the default lists. Admin can toggle "Show withdrawn children" on `/children`, and re-enrol a withdrawn child at any time |
| Manage lists (Admin) | `/admin/params` — add/remove values for classrooms, accident injury types/body parts, message contact methods and learning outcomes, without touching the database directly. Removing a classroom in use by an enrolled child or approved staff member is blocked with a clear message. Te Whāriki strands and attendance statuses are shown read-only, with an explanation of why (hard-coded elsewhere in the app / enforced by a DB constraint) |
| Library uploads (Admin) | `/library/new` — upload additional PDFs to the ECE document library and tag each one with a category (Compliance, Curriculum, Evaluation, Legislation, Practice guidance, Professional practice). Uploaded documents sit alongside the built-in set and can be removed again; the built-in set itself can't be deleted through the UI |
| Documentation gaps | First section of `/analytics`: every enrolled child with no published learning story in the last 2/4/6/8 weeks, never-written-about children first, with a "Write a story" shortcut. Added after UAT |
| Admin staff search | The Staff & families table on `/admin` can be searched by name/e-mail and filtered by role and status. Added after UAT |
| Tablet / phone layout | Below 760 px the sidebar turns into a top bar with a scrolling menu instead of disappearing. Added after UAT |
| Sign-up & approval | Parents/teachers self-register via `/signup`, choosing their centre (and classroom, if a teacher); accounts stay `pending` until an admin approves them from the Admin panel, at which point a parent can be linked to their child(ren) in the same step |

## Setup (VS Code, using venv)

### 1. Create and activate a virtual environment
```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```
In VS Code, select this `.venv` as your Python interpreter (Cmd/Ctrl+Shift+P →
"Python: Select Interpreter"). `.vscode/settings.json` already points at it.

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up your local database credentials
Create `app/db/connect.py` (this file is gitignored — it holds your real
local password and must never be committed):

```python
DB_HOST = 'localhost'
DB_PORT = 5432
DB_USER = 'postgres'
DB_NAME = 'whariki_connect'
DB_PASSWORD = 'your_local_postgres_password'
DB_AUTOCOMMIT = True

dbuser = DB_USER
dbpass = DB_PASSWORD
dbhost = DB_HOST
dbname = DB_NAME
dbport = DB_PORT
dbautocommit = DB_AUTOCOMMIT
```

### 4. Create the database and load the schema
```bash
createdb whariki_connect      # or create it via pgAdmin
psql -U postgres -d whariki_connect -f create_database.sql
```

### 5. Load static reference data
```bash
psql -U postgres -d whariki_connect -f populate_database.sql
```
This fills the `Params` table with fixed lookup values — classroom names,
*Te Whāriki* curriculum strands, accident-form body-part options, and
attendance statuses. It's plain SQL with no passwords, so it's kept
separate from account creation below.

### 6. Seed accounts and demo data
```bash
python generate_data.py
```
This is a Python script rather than SQL because every account's password
needs to be bcrypt-hashed before it's stored — something plain SQL can't
do on its own. It also **reads** classrooms and curriculum strands back out
of the `Params` table (rather than hardcoding them again), so the two
files stay in sync automatically.

This creates:
- **1 super admin**
- **6 teachers** (2 assigned to each of 3 classrooms: Piwakawaka, Kereru, Tui rooms)
- **20 children**, each with a basic profile (name, DOB, classroom, emergency contact)
- **40 parent accounts** (2 parents linked to each child)
- Demo content: today's attendance for every child, a few sample learning
  stories, and one sample accident form

**Every seeded account shares the same password:** `Sunnypreschool123`
(bcrypt-hashed before storage). Example logins:
```
admin@sunnypreschool.nz            (Admin)
sarah.thompson@sunnypreschool.nz   (Teacher)
```
Parent emails follow `firstname.lastname{index}@example.co.nz` — see the
`Users` table for the full list after seeding.

### 7. Run the app
In VS Code, just press **Run** on `run.py` (or F5 with the Python
extension), or from the terminal:
```bash
python run.py
```
Visit **http://127.0.0.1:5000**.

### Optional settings (`.env` next to `run.py`)
```
SECRET_KEY=any-long-random-string          # set this before deploying anywhere
GROQ_API_KEY=gsk_...                      # AI writing assistant
RSCRIPT_PATH=C:\Program Files\R\R-4.x.x\bin\Rscript.exe   # only if R isn't found automatically
SMTP_HOST=... SMTP_PORT=587 SMTP_USER=... SMTP_PASSWORD=... SMTP_FROM=...   # password-reset and approval e-mails
```

### Run the tests
```bash
python -m pytest -v
```
The suite in `tests/` (52 tests) creates its own throwaway users, children
and rooms (prefixed `pytest_` / `__pytest_room__`) and deletes them again
afterwards, so it runs safely against the normal development database. The
R tests are skipped automatically if R is not installed.

Two evaluation scripts in `evaluation/` produce the evidence used in the
final report (latest results are in `evaluation/results/`):
```bash
python evaluation/verify_chart_accuracy.py     # recomputes every chart value from the raw rows
python evaluation/measure_response_times.py    # median / p95 server response times per page
```

## Why one platform instead of integrating existing tools?

Existing NZ ECE tools solve one piece each — Storypark/Educa handle learning
stories but treat messaging as an afterthought; attendance/billing tools
handle admin but not documentation; parent communication happens informally
over email or WhatsApp, disconnected from either. APIs could move data
between them, but can't create one shared record where a learning story, an
absence, and a related parent message about the same event sit together in
context — and those platforms' APIs are closed or paid-tier anyway, making
real integration impractical for a small centre. Whāriki Connect solves the
underlying workflow problem directly: one login, one child profile, no
tab-switching during a busy classroom day.

## Notes for the assignment write-up

- Passwords are hashed with `Flask-Bcrypt` — see `app/utils.py` and
  `generate_data.py`.
- Access control is enforced server-side per request
  (`app/repository/child_repository.py: can_access_child`), not just hidden
  in the UI: parents can only reach their own children's records, teachers
  only their assigned classroom, admins see everything. This was verified
  by testing a parent account against another family's child record.
- The schema (`create_database.sql`) is deliberately relational — learning
  stories, attendance, messages and accident forms are all linked back to a
  single `Children` row — which is the structural argument for one
  integrated database over several separate systems glued together.
- Static reference data (classrooms, curriculum strands, accident-form body
  parts) lives in a `Params` lookup table, populated by
  `populate_database.sql` and read at runtime via
  `app/repository/param_repository.py` — the same "config data in the
  database, not hardcoded in the app" pattern used for dropdown options in
  the Tuatara project.
