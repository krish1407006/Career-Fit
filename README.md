# CareerAI — AI-Driven Career Development & Placement Assistance Platform

A full-stack placement preparation platform for final-year engineering students:
resume analysis, job matching, applications, skill quizzes, and a live voice mock
interview, with dedicated recruiter and admin workspaces.

---

## Table of contents

- [Stack](#stack)
- [Features](#features)
- [Roles and access model](#roles-and-access-model)
- [Project layout](#project-layout)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running the tests](#running-the-tests)
- [API reference](#api-reference)
- [Resume analysis](#resume-analysis)
- [Voice mock interview](#voice-mock-interview)
- [Security model](#security-model)
- [Privacy and scope](#privacy-and-scope)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite 8, React Router 7, Axios |
| Backend | Django 5, Django REST Framework 3.15 |
| Auth | JWT via `djangorestframework-simplejwt`, role-based permissions |
| Database | PostgreSQL 16 (SQLite for the test suite) |
| AI | External provider behind the `apps/ai` service layer (optional) |
| Lint / test | Oxlint, `node --test` |

Verified on Python 3.13.7, Node 22.17.0, npm 11.13.0.

---

## Features

**Student**

- Profile with education, projects, certifications and a manual skill catalogue
- Resume upload with server-side validation and AI-assisted analysis
- Skill-gap analysis against a chosen job
- Job browsing, filtering, match scoring and one-click apply
- Application tracking with status history
- Technical and aptitude quizzes with a server-timed attempt, review and history
- AI mock interview in voice or text mode, with a structured report
- Aggregated dashboard

**Recruiter**

- Company profile and job posting
- Skill requirements per job
- Applicant list with match scores and resume access
- Application status workflow (applied → shortlisted → interview → selected/rejected)
- Recruiter dashboard

**Admin**

- Every student capability on their own account, to exercise the real write paths
- Read-only inspection of all resumes, analyses, applications, quiz attempts and
  interview transcripts
- Quiz and question authoring
- Account management: role changes, activation, password reset, bulk delete
- "Super email" list, which grants admin rights by email address

---

## Roles and access model

Three roles: `student`, `recruiter`, `admin`.

`User.is_student` is a **capability** flag, true for the `student` role *and* for
admins, so an admin passes the same `IsStudent` permission the student pages use.
`User.role` stays `admin`, so role-gated routes and `/api/dashboard/` still land
the admin in the admin area.

An admin is therefore never impersonating anyone:

- **Writes are always their own.** An admin applying to a job creates an
  application owned by the admin, exactly as a student would.
- **Inspection is explicit and read only.** The admin screens are `APIView`s with
  only a `get` handler, so `POST`/`PUT`/`PATCH`/`DELETE` return 405.
- **Ownership is still enforced on writes.** Every student endpoint scopes its
  queries to `request.user`; a student asking for another student's resume,
  attempt or interview gets 404, not 403.
- **Filters do not leak.** `?student=`, `?quiz=` and `?status=` are ignored for
  non-admins rather than honoured.
- **The acting admin is protected.** Bulk delete refuses to remove the account
  performing the request.

Ownership failures return **404**, not 403, so a 403 never confirms that a record
exists.

---

## Project layout

```
backend/
  config/                settings, urls, wsgi/asgi
  apps/
    accounts/            user, profiles, auth, role permissions
    profiles/            education, projects, certifications, skills
    resumes/             upload, text extraction, AI analysis
    jobs/                skills, jobs, applications, matching
    assessments/         quizzes, questions, timed attempts
    interviews/          mock interview sessions and turns
    dashboard/           aggregated stats
    ai/                  provider isolation, prompts, offline fallbacks
  requirements.txt
frontend/
  src/
    api/                 axios client + per-feature API modules
    context/             auth provider
    hooks/               speech recognition, synthesis, audio level
    lib/                 speech helpers, formatting, labels
    components/          layout, shared UI, feature components
    pages/               student/, recruiter/, admin/, auth
  tests/                 node --test unit tests for the speech library
```

---

## Quick start

### 1. Prerequisites

- Python 3.11+
- Node 18+
- PostgreSQL 14+ (optional for the test suite)

### 2. Database

```sql
-- in psql as a superuser
CREATE USER careerai WITH PASSWORD '<your-password>';
CREATE DATABASE careerai OWNER careerai;
```

### 3. Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env        # then edit DB_PASSWORD
python manage.py migrate
python manage.py seed_demo    # optional demo users, jobs and quizzes
python manage.py runserver
```

The API is then on <http://127.0.0.1:8000/api/> and
<http://127.0.0.1:8000/api/health/> is a liveness probe that also checks the
database.

### 4. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` and `/media` to
`http://127.0.0.1:8000`, so no CORS configuration is needed in development.

### 5. Demo accounts

`python manage.py seed_demo` creates (and prints) these accounts:

| Role | Username | Password |
| --- | --- | --- |
| admin | `admin` | `Admin@123` |
| student | `student` | `Student@123` |
| recruiter | `recruiter` | `Recruiter@123` |

Use `python manage.py seed_demo --reset` to rebuild the demo data.

> These are development credentials for a locally seeded database. Do not run
> `seed_demo` against a deployment.

---

## Configuration

All configuration lives in `backend/.env`, which is git-ignored.
`backend/.env.example` documents every key.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | `django-insecure-dev-only` | Signs sessions and JWTs. **Required in production.** |
| `DJANGO_DEBUG` | `False` | `True` enables the dev error pages and any-origin CORS |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma separated host allow-list |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | — | PostgreSQL connection |
| `DJANGO_CORS_ALLOWED_ORIGINS` | empty | Comma separated frontend origins; used only when `DEBUG=False` |
| `DJANGO_SECURE_SSL` | `True` | HTTP→HTTPS redirect; only when `DEBUG=False` |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000` | HSTS max-age; only when `DEBUG=False` |
| `AI_PROVIDER` | empty | `openai` (OpenAI-compatible) or `gemini` |
| `AI_API_KEY` | empty | Provider key. Never commit a real one |
| `AI_BASE_URL` | empty | Override for OpenAI-compatible endpoints (Groq, OpenRouter, Ollama…) |
| `AI_MODEL` | `gpt-4o-mini` | Model name |
| `AI_REQUIRED` | `False` | `True` fails loudly instead of falling back offline |

The app **refuses to start** when `DJANGO_DEBUG=False` and the secret key is
still the development placeholder, so a deployment cannot silently run on a key
that is published in this repository.

### The AI key is optional

With no `AI_PROVIDER`/`AI_API_KEY` configured, the app stays fully functional.
Resume analysis falls back to a built-in rule-based checker and the interview
falls back to deterministic questions and evaluations. Both report their source
(`"offline"`) so a reader always knows whether AI was involved. Set
`AI_REQUIRED=True` to make provider failures surface as a clear message instead.

---

## Running the tests

### Backend

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test --settings=config.settings_test
```

`config/settings_test.py` swaps PostgreSQL for an in-memory SQLite database, so
the suite runs without a database server or `CREATEDB` rights.

Additional checks:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe manage.py check --deploy   # with production env vars
```

### Frontend

```powershell
cd frontend
npm test        # node --test, speech library
npm run lint    # oxlint
npm run build   # production bundle
```

---

## API reference

All endpoints are under `/api/`. Everything except registration, login, token
refresh and the health probe requires `Authorization: Bearer <access token>`.

### Authentication — `/api/auth/`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `register/` | Create a student or recruiter account |
| POST | `login/`, `token/` | Obtain access + refresh tokens |
| POST | `token/refresh/` | Rotate tokens |
| POST | `logout/` | Blacklist the refresh token |
| GET/PUT | `me/` | Current user and profile |
| GET/PUT | `me/email/` | Correct the address the super email list matches |
| GET | `admin/users/` | List every account (admin) |
| PATCH | `admin/users/<id>/` | Change role / activation (admin) |
| POST | `admin/users/<id>/reset-password/` | Set a new password (admin) |
| POST | `admin/users/bulk-delete/` | Delete selected accounts (admin) |
| GET/POST | `admin/super-emails/` | Manage the super email list |
| GET/PATCH/DELETE | `admin/super-emails/<id>/` | Single entry |

### Profile — `/api/`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET/PUT | `profile/` | Student profile |
| GET/POST | `profile/skills/` | Manual skills |
| DELETE | `profile/skills/<id>/` | Remove a skill |
| GET/POST | `education/`, `projects/`, `certifications/` | Own records |
| GET/PATCH/DELETE | `education/<id>/`, `projects/<id>/`, `certifications/<id>/` | Single record |

### Jobs and applications — `/api/`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `skills/` | Skill catalogue |
| GET | `jobs/` | Browse and filter active jobs |
| GET | `jobs/<id>/` | Job detail |
| GET | `jobs/<id>/match/` | Match score and missing skills |
| POST | `jobs/<id>/apply/` | Apply (one application per job) |
| GET | `jobs/mine/` | Recruiter's own jobs |
| GET | `jobs/<id>/applicants/` | Applicants for a job (recruiter owner) |
| GET | `applications/mine/` | The caller's applications |
| PATCH | `applications/<id>/status/` | Update status (recruiter owner) |
| GET | `skill-gap/` | Gap against a target job |
| GET | `recruiter/applications/` | Applications across the recruiter's jobs |

### Resumes — `/api/resumes/`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET/POST | `` | List own resumes / upload (multipart `file`) |
| GET/DELETE | `<id>/` | Own resume |
| GET | `<id>/download/` | Stream the file (owner, their recruiter, or admin) |
| POST | `<id>/analyze/` | Run or re-run AI analysis |
| GET | `<id>/analysis/` | Own stored analysis |
| GET | `admin/` | Every resume with its analysis (admin, read only) |
| GET | `admin/<id>/analysis/` | Full analysis for one resume (admin) |

`/api/resume-analyses/<id>/` returns a single analysis, owner only.

### Quizzes — `/api/`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `quizzes/`, `quizzes/<id>/` | List and detail |
| POST | `quizzes/<id>/start/` | Start or resume an attempt |
| POST | `quizzes/<id>/submit/` | Submit and score |
| GET | `quizzes/attempts/mine/` | The caller's attempts |
| GET | `quiz-attempts/<id>/` | Attempt review |
| GET/POST/PATCH/DELETE | `quizzes/admin/…` | Quiz and question authoring (admin) |

### Interviews — `/api/interviews/`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `start/` | Start an interview; `resume=true` continues the active one |
| GET | `mine/`, `` | The caller's sessions |
| GET | `active/` | Resume the in-progress session, 404 when there is none |
| GET | `<id>/` | Session state, current question, transcript |
| POST | `<id>/answer/` | Submit a transcript, get the evaluation and next question |
| POST | `<id>/complete/` | Finish early and build the report |
| POST | `<id>/cancel/` | Discard the interview |
| GET | `<id>/report/` | Final report, 409 while still running |
| GET | `admin/` | Every session with answer count and report score (admin) |

### Dashboards

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `dashboard/` | Role-aware router |
| GET | `dashboard/student/` | Student stats |
| GET | `dashboard/recruiter/` | Recruiter stats |
| GET | `dashboard/admin/` | Platform stats |

---

## Resume analysis

`POST /api/resumes/<id>/analyze/` extracts the PDF text (no OCR), sends it to the
AI service layer, validates the structured JSON answer, and stores it on
`ResumeAnalysis`.

- Only the owner can analyse or view an analysis; a foreign resume is a 404.
- Detected skills are added to the shared `Skill` catalogue and the student
  profile. Manual skills are never removed or renamed, and the API reports
  `"source": "ai" | "manual"` per skill.
- An optional `job_id` adds job-role relevance computed by the existing
  `apps/jobs/matching.py` logic, so there is no second matching algorithm.
- Provider errors never reach the client with keys, URLs or stack traces.
- The score describes document quality only. It is **not** a hiring probability,
  and the API returns that disclaimer alongside the number as `score_note`.

---

## Voice mock interview

The interview runs as a live browser conversation: the AI speaks a question, the
student records an answer, reviews the transcript, and gets feedback before the
next question.

**AI layer**

- `apps/ai/interview_service.py` owns the prompt, the provider call and output
  validation. It builds context from the profile, skills, target job, latest
  resume analysis and previous answers, then picks the next question category
  adaptively.
- `apps/ai/interview_offline.py` supplies deterministic questions, 0–10
  evaluations and a report, so the flow works with no AI key.
- `apps/interviews/services.py` orchestrates start/resume, answer persistence,
  follow-ups, completion, cancellation and report generation.

**Data model**

`InterviewSession` has a resumable `state`, `mode`, `job`, `started_at`,
`completed_at`, structured `report_data` and a safe `last_error`. `InterviewTurn`
stores structured `evaluation`, `category` and `source`. A conditional unique
constraint on `(session, client_token)` makes answer submission idempotent, so a
retried request is never scored twice.

**Behaviour**

- Only one interview may be active per student; a second start returns 409.
- If the AI call fails, the transcript is still saved and the same
  `client_token` can be retried.
- Refresh mid-interview returns the same state via `/active/`.

**Frontend**

- `src/hooks/useSpeechRecognition.js` wraps the vendor-prefixed
  `SpeechRecognition`. The microphone only records while the student holds the
  button, so a stray click can never start capturing audio.
- `src/hooks/useSpeechSynthesis.js` wraps `speechSynthesis` with a
  speak/cancel/repeat queue.
- `src/lib/speech.js` centralises support detection, error mapping, transcript
  cleanup, microphone level metering and idempotency token generation, and is
  covered by `frontend/tests/speech.test.js`.
- `VoiceInterviewPanel.jsx` drives the state machine (AI speaking, your turn,
  processing, evaluating, done) and the controls.

---

## Security model

**Authentication**

- JWT with refresh rotation and blacklisting on rotation
  (`ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`).
- Access tokens are held in memory and the refresh token in `localStorage`. The
  axios client refreshes a single time, replays the original request once, and
  coordinates across tabs so a rotated token is never blacklisted out from under
  a concurrent tab.
- Login failures return a single message for both an unknown username and a
  wrong password, so the endpoint cannot be used to enumerate accounts.

**Authorization**

- Every student endpoint filters by `request.user`. There is no endpoint that
  accepts a student id from the request body to widen the scope.
- Admin access is either the `admin` role, a Django superuser, or an address on
  the super email list. Editing that list is restricted to entries on it or to a
  superuser, so a plain admin cannot promote an arbitrary address.
- Admin inspection endpoints are read-only by construction.
- Resume downloads are limited to the owner, an admin, and a recruiter who has
  received that exact resume through an application to one of their jobs.

**Uploads**

- Resume uploads are limited to PDF by extension, by size (10 MB) and by
  **content**: the file must actually begin with a PDF header. The name and the
  browser-supplied content type are both attacker controlled, so neither is
  trusted.
- Files are stored under a random UUID in a per-user directory. The original
  filename is stored as a field, never as a path, so it cannot traverse
  directories.
- Downloads are sent as `attachment` with `nosniff`, a `sandbox` CSP and
  `no-store`, so an uploaded document is never interpreted as active content in
  the app's own origin.

**Configuration**

- `DEBUG` defaults to `False`, and the app refuses to start with `DEBUG=False`
  and the placeholder secret key.
- With `DEBUG=False`: HSTS, secure session/CSRF cookies, HTT→HTTPS redirect,
  `nosniff`, `DENY` framing, same-origin referrer and COOP are all enabled, and
  the CORS allow-list is explicit.
- The browsable API renderer is development-only, so a production deployment
  does not publish a browsable index of every endpoint.
- Upload limits are bounded in Django settings as well as in the serializer, so
  an oversized body cannot buffer in memory before validation runs.

**AI provider isolation**

- The rest of the system never imports a vendor SDK. All calls go through
  `apps/ai/providers.py`, which converts transport, credential and shape errors
  into typed errors that carry no key, URL or traceback.
- Keys are read from settings per call and never cached beyond a request.

**Scoring and privacy**

- Resume text, provider payloads, interview transcripts and stack traces are
  never sent to the client.
- No raw microphone audio is stored, uploaded or sent to the AI provider; only
  the recognised transcript is saved, and only after submission.

---

## Privacy and scope

- **No raw microphone audio** is stored, uploaded or sent to the AI provider.
- No video, facial, emotion, accent or personality analysis.
- No question or prompt asks for age, gender, religion, caste, health,
  disability, marital status or any other protected characteristic.
- Scores are self-practice indicators from an AI coach. They are not objective
  ability, not a hiring decision, and every report repeats that next to the
  score.

---

## Deployment

1. Set real values in `backend/.env` — in particular a generated
   `DJANGO_SECRET_KEY` and the real `DJANGO_ALLOWED_HOSTS`.
2. Set `DJANGO_DEBUG=False`.
3. Install the backend with a production WSGI server:

   ```powershell
   pip install gunicorn          # Linux/macOS
   gunicorn config.wsgi:application --bind 0.0.0.0:8000
   ```

   On Windows use `waitress`:

   ```powershell
   pip install waitress
   waitress-serve --port=8000 config.wsgi:application
   ```

4. Run `python manage.py migrate` and `python manage.py collectstatic`.
5. Build the frontend with `npm run build` and serve `frontend/dist` from any
   static host or CDN.
6. Put a TLS-terminating reverse proxy in front of both. When TLS terminates at
   the proxy, `SECURE_PROXY_SSL_HEADER` is already configured, so Django reads
   the real scheme correctly. Set `DJANGO_SECURE_SSL=False` only if the proxy
   already redirects HTTP to HTTPS, otherwise every plain request gets a 301.
7. Set `DJANGO_CORS_ALLOWED_ORIGINS` to the exact frontend origin.
8. Serve uploaded resumes from durable storage — they are not in the build
   output, and `MEDIA_ROOT` is `backend/media`.

Verify a deployment before handing it over:

```powershell
.\.venv\Scripts\python.exe manage.py check --deploy
```

This reports 0 issues when the production environment is configured correctly.

---

## Troubleshooting

**`RuntimeError: DJANGO_SECRET_KEY is still the development placeholder`**
`DJANGO_DEBUG=False` with the default key. Generate a real one:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

**`Bad Request (400)` on every request in production**
The real hostname is missing from `DJANGO_ALLOWED_HOSTS`.

**`DisallowedHost` / CORS errors from the browser**
Set `DJANGO_CORS_ALLOWED_ORIGINS` to the exact frontend origin. It is only read
when `DJANGO_DEBUG=False`.

**Tests cannot create a test database**
The PostgreSQL role lacks `CREATEDB`. Run the suite with the SQLite settings:

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.settings_test
```

**"Voice input is not supported in this browser"**
Speech recognition needs a Chromium-based browser, and the microphone requires
a secure context: `localhost` or HTTPS. The panel explains this and offers a
text input instead, so the interview still works.

**Analysis says `source: "offline"`**
No `AI_PROVIDER`/`AI_API_KEY` is configured, or the provider call failed and
fell back. The feature still works; this is the intended fallback. Set
`AI_REQUIRED=True` to see the error instead of the fallback.

**Upload rejected as "not a PDF"**
The file does not start with a PDF header, regardless of its name. Scanned
images exported without OCR, and renamed `.docx`/`.txt` files, are rejected by
design.
