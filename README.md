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
- **admin** — manage users, jobs, applications, quizzes

## Project layout

```
backend/                Django project
  config/               settings, urls, wsgi
  apps/
    accounts/           user + profiles + auth + role permissions
    resumes/            resume upload + AI skill extraction
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
- AI provider/keys/endpoint are read from `.env` via `apps/ai`. No provider SDKs are imported in feature code — swap providers by adding a function in `apps/ai/providers.py` and setting `AI_PROVIDER`.