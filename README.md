# Research Blog Reading Tracker

Monorepo MVP for a guided reading system focused on AI/AIGC research blogs.

## Stack

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + SQLModel + SQLite
- RSS ingestion: feedparser
- Deployment: Docker Compose

## Features in this MVP slice

- RSS source CRUD
- Source enable/disable
- RSS validation and manual fetch
- Article deduplication by URL
- Inbox view for uncategorized articles
- Manual article entry
- Settings persistence for OpenAI key, model, UI language, and feature toggle
- Placeholder routes for curriculum, today, log, progress, and weekly review

## Repository layout

- `frontend/`: Next.js app
- `backend/`: FastAPI app
- `docker-compose.yml`: local and server deployment entrypoint

## Local development

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`.

The Next.js app proxies `/backend-api/*` to the FastAPI backend, so browser code can stay same-origin in both local and deployed environments.

## Environment variables

Copy root `.env.example` if you want to customize defaults.

- `BACKEND_INTERNAL_URL`: internal backend address used by the frontend proxy
- `NEXT_PUBLIC_API_BASE_URL`: frontend API base path, defaults to `/backend-api`
- `BACKEND_CORS_ORIGINS`: allowed browser origins for FastAPI
- `DATABASE_URL`: SQLite path for the backend
- `APP_ENV`: application environment label

## Seed data

The backend seed script inserts these sources if they do not already exist:

- Hugging Face Blog
- Lil'Log
- BAIR Blog
- 科学空间

Run:

```bash
cd backend
python -m app.seed
```

## Tests and checks

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm run lint
```

## Docker deployment

For local production-like startup or an Ubuntu/Debian server:

```bash
docker compose up --build -d
```

The stack exposes:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

SQLite data is persisted in the named volume `backend_data`.

## Git-to-server deployment flow

Typical server workflow:

```bash
git pull
docker compose up --build -d
```

This MVP does not yet include HTTPS, reverse proxy, CI/CD, or automated background scheduling.
