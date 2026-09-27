# CareerAI — AI-Driven Career Development & Placement Assistance Platform

Full-stack placement preparation platform for B.Tech final year project.

## Stack

- Frontend: React 19 + Vite + React Router + Axios
- Backend: Django 5 + Django REST Framework
- Auth: JWT (djangorestframework-simplejwt) with role-based permissions
- Database: PostgreSQL 16
- AI: external provider behind `apps/ai` service layer (optional; key off by default)

## Roles

- **student** — profile, resume AI analysis, skill-gap, job matching, applications, quizzes, AI mock interview, dashboard
- **recruiter** — company profile, post/manage jobs, review candidates, update application status
- **admin** — every student feature on their own account, plus read-only inspection of all student data

### Admin capabilities

An admin is not impersonating anyone. `User.is_student` is a *capability* flag that
is true for the `student` role **and** for admins, so the admin passes the same
`IsStudent` permission the student pages use. `User.role` stays `admin`, so
`/api/dashboard/` and `RequireRole` still land the admin on the admin area.

- **Full student writes.** The admin dashboard links into the student area
  (profile, resume upload + AI analysis, job matching, apply, quizzes, mock
  interview). Everything an admin does there is written against their own
  account, which exercises the real write paths a student uses. The admin's own
  rows then show up in the inspection screens below, labelled with their
  username.
- **Read-only inspection.** Separate screens list every student's resumes, AI
  analyses, applications, quiz attempts and interview transcripts. They are
  `ListAPIView`s: `POST`/`PUT`/`PATCH`/`DELETE` return 405, so an inspection
  screen can never mutate another student's record.
- **Admins are not students.** `?student=`, `?quiz=` and `?status=` filters on
  the inspection endpoints are ignored for non-admins rather than honoured, and
  a student asking for `/api/admin/applications/` gets a 403. A recruiter
  calling `/api/quiz-attempts/` still only ever sees their own (empty) list.
- **Ownership still applies to writes.** An admin applying to a job creates an
  application owned by the admin, exactly as a student would.


## Project layout

```
backend/                Django project
  config/               settings, urls, wsgi
  apps/
    accounts/           user + profiles + auth + role permissions
    resumes/            resume upload + AI resume analysis (analysis.py)
    jobs/               skills, jobs, applications, matching
    assessments/        quizzes (technical / aptitude)
    interviews/         AI mock interview sessions
    dashboard/          aggregated stats endpoints
    ai/                 external AI service layer (provider isolation)
frontend/               React + Vite SPA
  src/api/              axios client, auth api, feature apis
  src/context/          auth context
  src/components/       layout, shared UI
  src/pages/            feature pages
```

## Setup (Windows / PowerShell)

### 1. Database

Install PostgreSQL 16. Create the DB once:

```powershell
# in psql as superuser
CREATE USER careerai WITH PASSWORD '<your-password>';
CREATE DATABASE careerai OWNER careerai;
```

### 2. Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env     # fill in DB_PASSWORD (and AI keys when ready)
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev                # http://localhost:5173 (proxies /api to :8000)
```

## Security & configuration

- All secrets live in `backend/.env` (git-ignored). `backend/.env.example` documents keys.

## Phase 6 - AI resume analysis

`POST /api/resumes/<id>/analyze/` extracts the PDF text (existing
`apps/resumes/text_extraction.py`, no OCR), sends it to the AI service layer
(`apps/ai/resume_analyzer.py` -> `apps/ai/providers.py`), validates the
structured JSON answer and stores it on `ResumeAnalysis`.

- `GET /api/resumes/<id>/analysis/` and `GET /api/resume-analyses/<id>/` read it back.
- Only the resume owner can analyse or view an analysis; a foreign resume is a 404.
- AI-detected skills are added to the shared `Skill` catalogue and the student's
  profile; manual skills are never removed or renamed. The API reports
  `"source": "ai" | "manual"` per skill.
- `job_id` in the analyse body adds job-role relevance computed by the existing
  `apps/jobs/matching.py` logic (no second matching algorithm).
- Without `AI_PROVIDER`/`AI_API_KEY` the endpoint falls back to the built-in
  rule-based checker and flags `source: "offline"`; set `AI_REQUIRED=True` to
  fail with a message instead. Provider errors never reach the client with keys,
  URLs or stack traces.
- The analysis score describes document quality only - it is not a hiring
  probability.

## Phase 7 - real-time voice mock interview

The mock interview runs as a live browser conversation: the AI speaks each
question, the student records an answer with the microphone, reviews the
recognised transcript, and gets structured feedback before the next question.

### AI layer

- `apps/ai/interview_service.py` owns the prompt, the provider call and output
  validation. It builds context from the student profile, profile skills, the
  target job, the latest resume analysis and the answers given so far, then
  picks the next question category adaptively.
- `apps/ai/interview_offline.py` supplies deterministic questions, 0-10
  structured evaluations and a report, so the whole flow works with no AI key.
- `apps/interviews/services.py` orchestrates start/resume, answer persistence,
  follow-ups, completion, cancellation and report generation.
- `AI_PROVIDER`/`AI_API_KEY` are read from `.env` only. `AI_REQUIRED=True` makes
  provider failures surface as a message instead of falling back to offline.

### Data model

`InterviewSession` gained `job`, `mode`, resumable `state`, `started_at`,
`completed_at`, structured `report_data` and a safe `last_error`;
`InterviewTurn` gained structured `evaluation`, `category` and `source`. A
conditional unique constraint on `(session, client_token)` makes answer
submission idempotent so a retried request is never double-scored.

### API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/interviews/start/` | Start a voice or text interview; `resume=true` continues the active one |
| GET | `/api/interviews/` | All sessions (staff) |
| GET | `/api/interviews/mine/` | The student's own sessions |
| GET | `/api/interviews/active/` | Resume the in-progress session, 404 when there is none |
| GET | `/api/interviews/<id>/` | Session state, current question and transcript |
| POST | `/api/interviews/<id>/answer/` | Submit a transcript, get evaluation and the next question |
| POST | `/api/interviews/<id>/complete/` | Finish early and build the report |
| POST | `/api/interviews/<id>/cancel/` | Discard the interview |
| GET | `/api/interviews/<id>/report/` | Final report, 409 while still running |

#### Admin inspection endpoints

All of these require an admin and are read only.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/resumes/admin/` | Every resume, with its analysis inlined; `?student=` and `?status=` |
| GET | `/api/resumes/admin/<id>/analysis/` | The full analysis for one resume |
| GET | `/api/admin/applications/` | Every application; `?student=`, `?status=`, `?job=` |
| GET | `/api/interviews/admin/` | Every session, with answer count and report score; `?student=`, `?status=` |
| GET | `/api/quiz-attempts/` | Admin sees every attempt; filter with `?student=`, `?quiz=`, `?status=` |
| GET | `/api/quiz-attempts/<id>/` | Attempt review, for any student |
| GET | `/api/resumes/<id>/download/` | The PDF itself |
| GET | `/api/interviews/<id>/` | Full transcript and report for any session |

The resume, application, interview and attempt payloads all carry
`student_username` / `student_id` so a screen can say whose record it is showing.


- Only one interview may be active per student; a second start returns 409
  `interview_in_progress`.
- Every endpoint derives ownership from `request.user`. Another student's
  session, answer or report is a 404, never a 403 that confirms it exists.
- If the AI call fails, the transcript stays saved and the same `client_token`
  can be retried. Nothing is scored twice.

### Frontend

- `src/hooks/useSpeechRecognition.js` wraps `SpeechRecognition`. The microphone
  only records while the student holds the button, so a stray click can never
  start capturing audio.
- `src/hooks/useSpeechSynthesis.js` wraps `speechSynthesis` with a speak /
  cancel / repeat queue.
- `src/components/interviews/VoiceInterviewPanel.jsx` drives the state machine
  (AI speaking, your turn, processing, evaluating, done) and the controls.
- `src/components/interviews/InterviewReport.jsx` renders the overall score,
  strengths, areas to improve, topics to prepare and per-question feedback.
- `src/lib/speech.js` centralises browser support detection, error mapping,
  transcript cleanup and idempotency token generation.

### Privacy and scope

- **No raw microphone audio is stored, uploaded or sent to the AI provider.**
  Only the recognised transcript is saved, and only after the student submits
  it.
- No video, facial, emotion, accent or personality analysis.
- No question or prompt ever asks for age, gender, religion, caste, health,
  disability, marital status or any other protected characteristic.
- Scores are self-practice indicators from an AI coach, not objective ability
  and not a hiring decision. The report repeats this next to the score.
- Speech recognition is Chromium-based in practice; when it is unavailable the
  panel explains why and the student types the answer instead. The microphone
  needs `localhost` or HTTPS.
