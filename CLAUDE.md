# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Media Tools is a local web workstation for batch-downloading Douyin (TikTok China) and Bilibili videos, plus transcribing local media files, via the Tongyi Qwen cloud service. The entire UI is in Simplified Chinese.

## Architecture

Monorepo with two independent codebases:

- **Backend** (`src/media_tools/`): Python 3.11+ / FastAPI + SQLite3 (WAL mode, no ORM) + APScheduler
- **Frontend** (`frontend/`): React 19 + Vite 8 + TypeScript 6 + Tailwind CSS 4 + shadcn/ui (base-ui) + Zustand 5

### Backend modules

- `api/` — FastAPI app and routers (creators, assets, tasks, settings, douyin, scheduler). App lifespan in `api/app.py` calls `init_db()` and `scheduler.startup_scheduler()`; `scheduler.start()` runs there, **not** at module import — keep it that way.
- `api/routers/tasks.py` — task CRUD, cancel/retry/rerun/pause/resume endpoints. Error responses use `HTTPException` (proper HTTP status codes), **never** return `{"status":"error"}` with HTTP 200.
- `api/websocket_manager.py` — WebSocket endpoint at `/api/v1/tasks/ws` for real-time task progress, with 20s heartbeat ping
- `api/routers/scheduler.py` — APScheduler-backed cron scheduling for automated full-sync; CRUD for scheduled tasks, toggle enable/disable, and manual trigger
- `douyin/` — Douyin video downloading via the F2 library, creator management, cookie/auth handling
- `bilibili/` — Bilibili downloading and creator management (peer of `douyin/`)
- `pipeline/download_router.py` — `resolve_platform(url)` dispatches a URL to the Douyin or Bilibili downloader; router for any cross-platform call
- `pipeline/worker.py` — entry point called by task routers (`run_pipeline_for_user`, `run_batch_pipeline`, `run_download_only`, `run_local_transcribe`). State files use `get_project_root()` paths, **never** CWD-relative.
- `pipeline/orchestrator_v2.py` — concurrent transcription (configurable via `PIPELINE_CONCURRENCY`, default 10) and automatic account rotation via `AccountPool` class
- `pipeline/state_manager.py` —断点续传状态持久化，原子写入（先写 `.tmp` 再 `os.replace()`）
- `transcribe/` — Playwright-driven Qwen transcription: OSS upload → transcribe → export markdown. Multi-account support via `transcribe/db_account_pool.py`
- `db/core.py` — centralised schema definitions for all tables and `init_db()`; single source of truth for DDL
- `services/` — business logic extracted from routers (task_ops, task_state, file_browser, qwen_status, etc.)
- `repositories/` — data access layer for task_queue, creators, assets tables
- `workers/` — background task workers (pipeline_worker, full_sync_worker, local_transcribe_worker, creator_sync)
- `core/config.py` — unified config system; DB `SystemSettings` table is the single source of truth for runtime settings

### Frontend structure

- 3 pages: `Creators` (default), `Discovery`, `Settings`
- Global `Sidebar` (w-64) with nav + theme toggle + `TaskMonitorPanel`
- Reusable `Toggle` component in `components/ui/toggle.tsx` (used in Creators and Settings for auto-save switches)
- Skeleton loading states (`Skeleton` from shadcn/ui) used across pages for initial data fetch
- Guided empty states with call-to-action when no data is present
- State via Zustand store (`store/useStore.ts`): tasks from WebSocket, settings from REST. `fetchCreators`/`fetchAssets` have in-flight deduplication guards.
- API services in `services/*.ts` (split from `lib/api.ts` barrel). All functions support `AbortSignal` for request cancellation.
- UI components use shadcn/ui built on `@base-ui/react` (not Radix)
- WebSocket disconnect indicator in `TaskMonitorPanel`
- Path alias: `@/*` maps to `src/*`

### Data flow

1. User submits a Douyin or Bilibili URL → backend fetches metadata via the platform-specific handler
2. User selects videos → backend creates a task (pipeline/download); `pipeline/download_router.py::resolve_platform` routes to the right downloader
3. Task progress pushed to frontend via WebSocket
4. Pipeline: download video → upload to Qwen OSS → Playwright transcribe → save markdown (concurrent by default, uses AccountPool for multi-account rotation)
5. Frontend polls creators/assets on `lastCompletedTaskTime` change
6. Local file transcription: user selects a local video/audio file → backend skips download step → upload to Qwen OSS → Playwright transcribe → save markdown (endpoint: `POST /api/v1/tasks/transcribe/local`)

## Commands

### Start everything
```bash
./run.sh              # backend (8000) + frontend (5173), auto-installs deps
./run.sh backend      # backend only
./run.sh frontend     # frontend only
```

### Backend
```bash
# Activate the project virtualenv first — the repo requires Python 3.11+
# (uses `str | None`, `from datetime import UTC`, `@dataclass(slots=True)`).
# System `python` is often 3.9 and will fail with confusing import errors.
source .venv/bin/activate

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
- **Config**: Runtime config in `config/config.yaml` (managed by `douyin/core/config_mgr.py`). Transcribe env vars in `config/transcribe/.env`. Pipeline env vars prefixed `PIPELINE_*`, Qwen env vars prefixed `QWEN_*`. Runtime settings (auto_transcribe, auto_delete, concurrency, api_key) are in DB `SystemSettings` table — the single source of truth. `config.yaml` is read-only for runtime.
- **API prefix**: All REST endpoints under `/api/v1/`. Routers mounted in `api/app.py`.
- **API errors**: Always use `HTTPException` with proper status codes (404, 409, 500). The global error handler converts them to `{"code","message","details"}`. **Never** return `{"status":"error"}` with HTTP 200.
- **Auth**: Optional API key middleware in `app.py`. If `api_key` is set in SystemSettings, all requests (except health/ws/docs) require `Authorization: Bearer <key>`.
- **Frontend components**: shadcn/ui components in `frontend/src/components/ui/`. Use existing `ConfirmDialog` for destructive actions. Use existing `Dialog` (base-ui backed) for modals.
- **TypeScript**: Strict mode enabled. Exports and interfaces for API responses defined in `types/index.ts`. API services in `services/*.ts`.
- **Styling**: Tailwind CSS 4 with Apple-inspired design tokens defined in `index.css`. Dark mode via `next-themes` with `.dark` class variant.
- **Toasts**: Use `sonner`'s `toast.success()` / `toast.error()`. The Axios interceptor already toasts on 4xx/5xx errors, so page-level catch blocks **must not** duplicate the toast.
- **Zustand caching**: Creators/Assets data fetched via `useStore` and cached for 30 seconds. The store has in-flight deduplication — concurrent callers share the same Promise. Components should call the store's fetch action rather than hitting the API directly.
- **AbortSignal**: All frontend API service functions accept an optional `signal?: AbortSignal` parameter. Use it for cancellable requests (page navigation, component unmount).
- **State files**: Pipeline state files (`.pipeline_state_*.json`) are stored in `get_project_root()` directory and written atomically (temp file + rename). They are in `.gitignore`.

## AI 协作规范

### 生成后强制自检（每条必须做）
- [ ] 检查所有异步函数是否有 await（Python）/async-await（JS）
- [ ] 检查边界条件：空列表、None、空字符串
- [ ] 检查变量命名：Python 用 snake_case，JS/TS 用 camelCase
- [ ] 检查异常处理：禁止裸 except Exception，必须指定类型
- [ ] 检查类型：新增代码 mypy/pyright 必须 0 错误

### 敏感信息处理（红色警戒线）
- 看到 cookie/api_key/token，立刻停止，询问加密方案
- 禁止在日志/错误信息中打印敏感字段

### 代码债务红线（禁止新增）
- 禁止新增裸 except Exception
- 禁止新增重复代码（先查现有 utils/helpers）
- 禁止新增硬编码（配置必须走 config 文件）

### 交付标准
- 代码 + 自检报告 + 潜在风险说明 = 完成
- 只有代码 = 未完成
