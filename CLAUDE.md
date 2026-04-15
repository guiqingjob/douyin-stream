# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Media Tools is a local web workstation for batch-downloading Douyin (TikTok China) videos and transcribing them via Tongyi Qwen cloud service. The entire UI is in Simplified Chinese.

## Architecture

Monorepo with two independent codebases:

- **Backend** (`src/media_tools/`): Python 3.11+ / FastAPI + SQLite3 (WAL mode, no ORM) + APScheduler
- **Frontend** (`frontend/`): React 19 + Vite 8 + TypeScript 6 + Tailwind CSS 4 + shadcn/ui (base-ui) + Zustand 5

### Backend modules

- `api/` — FastAPI app and routers (creators, assets, tasks, settings, douyin, scheduler)
- `api/routers/tasks.py` — includes a WebSocket endpoint at `/api/v1/tasks/ws` for real-time task progress
- `api/routers/scheduler.py` — APScheduler-backed cron scheduling for automated full-sync; CRUD for scheduled tasks, toggle enable/disable, and manual trigger
- `douyin/` — video downloading via the F2 library, creator management, cookie/auth handling
- `transcribe/` — Playwright-driven Qwen transcription: OSS upload → transcribe → export markdown
- `pipeline/` — orchestration layer connecting download and transcription; `worker.py` is the entry point called by task routers
- `db/core.py` — centralised schema definitions for all 7 tables and `init_db()`; single source of truth for DDL

### Frontend structure

- 4 pages: `Creators` (default), `Discovery`, `Inbox`, `Settings`
- Global `Sidebar` (w-64) with nav + theme toggle + `TaskMonitorPanel`
- Reusable `Toggle` component in `components/ui/toggle.tsx` (used in Creators and Settings for auto-save switches)
- Skeleton loading states (`Skeleton` from shadcn/ui) used across pages for initial data fetch
- Guided empty states with call-to-action when no data is present
- State via Zustand store (`store/useStore.ts`): tasks from WebSocket, settings from REST
- API client in `lib/api.ts`, task display helpers in `lib/task-utils.ts`
- UI components use shadcn/ui built on `@base-ui/react` (not Radix)
- WebSocket disconnect indicator in `TaskMonitorPanel`
- Path alias: `@/*` maps to `src/*`

### Data flow

1. User submits a Douyin URL → backend fetches metadata via F2
2. User selects videos → backend creates a task (pipeline/download)
3. Task progress pushed to frontend via WebSocket
4. Pipeline: download video → upload to Qwen OSS → Playwright transcribe → save markdown
5. Frontend polls creators/assets on `lastCompletedTaskTime` change
6. (Planned) Local file transcription: user uploads a local video/audio file → backend skips download step → upload to Qwen OSS → Playwright transcribe → save markdown

## Commands

### Start everything
```bash
./run.sh              # backend (8000) + frontend (5173), auto-installs deps
./run.sh backend      # backend only
./run.sh frontend     # frontend only
```

### Backend
```bash
# Run the API server directly
PYTHONPATH=src python -m uvicorn media_tools.api.app:app --reload --host 127.0.0.1 --port 8000

# Health check
curl http://127.0.0.1:8000/api/health

# Run all tests
pytest

# Run a single test file
pytest tests/api/test_creators.py

# Run a specific test
pytest tests/api/test_creators.py::test_function_name -v
```

### Frontend
```bash
cd frontend
npm run dev           # Vite dev server on 5173
npm run build         # tsc -b && vite build
npm run lint          # ESLint (flat config, ESLint 9)
npx tsc --noEmit      # Type check only
```

## Key Conventions

- **Database**: Raw `sqlite3` module, no ORM. Connection per request, close in finally. WAL mode.
- **Config**: Runtime config in `config/config.yaml` (managed by `douyin/core/config_mgr.py`). Transcribe env vars in `config/transcribe/.env`. Pipeline env vars prefixed `PIPELINE_*`, Qwen env vars prefixed `QWEN_*`.
- **API prefix**: All REST endpoints under `/api/v1/`. Routers mounted in `api/app.py`.
- **Frontend components**: shadcn/ui components in `frontend/src/components/ui/`. Use existing `ConfirmDialog` for destructive actions. Use existing `Dialog` (base-ui backed) for modals.
- **TypeScript**: Strict mode enabled. Exports and interfaces for API responses defined in `lib/api.ts`.
- **Styling**: Tailwind CSS 4 with Apple-inspired design tokens defined in `index.css`. Dark mode via `next-themes` with `.dark` class variant.
- **Toasts**: Use `sonner`'s `toast.success()` / `toast.error()`. Note: the Axios interceptor already toasts on errors, so page-level catch blocks should not duplicate the toast.
- **Zustand caching**: Creators data is fetched via `useStore` and cached for 30 seconds (`lastFetchTime` guard). Components should call the store's fetch action rather than hitting the API directly; the store deduplicates requests within the cache window.
