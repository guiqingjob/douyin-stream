# Parallel Claude Code Work Plan — 2026-04-18

Two Claude Code sessions run in parallel on this repo. This doc is the shared
contract for file ownership, task scope, and coordination. **Read it before
touching anything.**

---

## 0. Starting state

Branch: `main` (and the nested `frontend/` repo on `webui-apple-design`)

Last shipped commits on `main`:

```
d07fe53 perf(search): move transcript body into SQLite, drop per-file reads
ef11436 feat(api): POST /assets/bulk_delete
54c032c chore: bump frontend for inbox TDZ fix
797d928 chore: bump frontend for j/k keyboard navigation
b24f740 feat(api): transcript_preview column + backfill
8707640 feat(api): expose asset times, creator unread count, bulk mark endpoint
9bb98f2 feat(ws): server-side heartbeat for task progress channel
e6d5343 fix: download-only, regex, and scheduler import-time bugs
```

Tests green: 157/157 pytest, `tsc --noEmit` clean.

**Heads-up**: the long-running dev uvicorn (PID 4233) has stopped picking up
`--reload`. Both sessions should restart it (`./run.sh backend`) the first
time they need to hit a new endpoint.

---

## 1. Ground rules (BOTH sessions obey)

### Git hygiene
- `git pull --rebase` before every commit. If your rebase has conflicts in a
  file you weren't supposed to touch, the other session broke the contract —
  stop and flag, don't paper over.
- Commits are small, one logical change each, and use the repo's existing
  style (`feat(scope): …`, `fix(scope): …`, `perf(…): …`, `chore: …`).
- **Never** rewrite history on `main` or the frontend branch. No force-push.
- **Never** edit the frontend and outer repo in the same commit. The
  frontend is a nested git repo; commit there first, then `git add frontend
  && git commit` on the outer to bump the pointer.

### File ownership
- If a file is listed under another session's ownership, **do not touch it**
  even for a one-line fix. Open a note in this doc's `## 4. Cross-session
  notes` section instead.
- Shared files (`frontend/src/lib/api.ts`, `CLAUDE.md`) are **append-only**
  for both sessions — add new exports at the end of the relevant section,
  don't reshape existing code. If you need to reshape, coordinate in
  section 4 first.

### Tests & acceptance
- Every commit must pass `pytest` (backend) and `npx tsc --noEmit` (frontend)
  before pushing.
- If you add a backend endpoint, smoke-test it against a scratch uvicorn on
  an unused port (8766–8799 range) before calling it done. The existing
  `./run.sh backend` on 8000 is the user's dev instance — leave it alone.

### Scope discipline
- Don't "clean up" unrelated code you notice on the way. Drop a note in
  `## 4` instead.
- Don't touch `docs/` except to update this file.

---

## 2. Work tracks

### Track A — Task cancellation (reliability)

**Problem**: backend task workers run under FastAPI `BackgroundTasks` which
are fire-and-forget. Today a stuck task hangs until the 2-hour stale timeout
(`tasks.py:21 STALE_TASK_HOURS`). There is no cancel endpoint, no cancel
button. This is the #1 user-visible reliability gap.

**Files Track A OWNS (exclusive write access)**:
- `src/media_tools/api/routers/tasks.py`
- `src/media_tools/db/core.py` *(for the one-line `_ensure_column` migration
  only — do not touch unrelated columns)*
- `frontend/src/components/layout/TaskMonitorPanel.tsx`
- `frontend/src/store/useStore.ts`

**Shared files Track A may append to (coordinate line ranges if needed)**:
- `frontend/src/lib/api.ts` — append `cancelTask(taskId)` near the existing
  `getTaskStatus` function in the tasks section. Do NOT edit the scheduler
  section.

**Plan**:
1. **DB migration**: `_ensure_column(conn, "task_queue", "cancel_requested",
   "INTEGER DEFAULT 0")`. Also treat `status='CANCELLED'` as a valid
   terminal state.
2. **Worker registry**: in `tasks.py` keep a module-level
   `dict[task_id, asyncio.Task]`. Move the `background_tasks.add_task(...)`
   calls to `asyncio.create_task(...)` and store the handle. Delete the
   entry in the worker's `finally`.
3. **Cancellation token**: each `_background_*_worker` accepts a simple
   `CancellationToken` (bool wrapper). Workers check it at natural progress
   points — between URL downloads, between transcript items, before DB
   writes — and raise `asyncio.CancelledError` if flipped.
4. **Endpoint**: `POST /api/v1/tasks/{task_id}/cancel` flips the token,
   calls `.cancel()` on the registered task if present, writes
   `status='CANCELLED'` in DB, broadcasts WS update. 404 if task not
   registered AND not in DB.
5. **Stale cleanup exclusion**: `cleanup_stale_tasks` already does
   `WHERE status IN ('PENDING', 'RUNNING')` — confirm `CANCELLED` stays
   outside that set.
6. **Frontend API**: `cancelTask(id)` in `lib/api.ts`. TaskMonitorPanel
   shows a 🛑 button next to `RUNNING` tasks that calls it. `task-utils.ts`
   treats `CANCELLED` as terminal (status label "已取消", gray tone).
7. **Retry + cancel**: when the user clicks 重试 on a `RUNNING` task, call
   cancel first then re-submit (avoids duplicate Playwright sessions).
   Wait for the task status to leave RUNNING before re-submitting, capped
   at 2s.

**Acceptance**:
- `pytest` still 157/157.
- `tsc --noEmit` clean.
- Smoke: start a real pipeline task, POST `/cancel`, confirm DB row flips
  to `CANCELLED` within 5s and the WS broadcast arrives.
- A cancelled task shows gray "已取消" in the task panel and no longer
  shows a spinner. 🛑 button no longer visible on it.

**Risks / known caveats to handle**:
- Playwright sessions aren't interruptable mid-operation. That's fine —
  cancel only stops *queuing more work* between items; an in-flight
  transcription for one item finishes naturally. Document this in a
  toast or the task detail message.
- Background tasks spawned before this change don't know about the
  registry. Restart uvicorn to land the new code.

---

### Track B — Scheduler first-class UI (polish / feature)

**Problem**: backend already has full scheduler CRUD
(`/scheduler/ GET/POST`, `/scheduler/{id}/toggle PUT`, `/scheduler/{id}
DELETE`, `/scheduler/run_now POST`) but the frontend only exposes a single
hardcoded "daily 02:00" toggle on the Creators page. Users can't set a
custom cron, delete a schedule, run-now, or create multiple schedules.

**Files Track B OWNS (exclusive write access)**:
- `frontend/src/pages/Settings.tsx`
- `frontend/src/components/` *(any new files under `scheduler/`)*

**Shared files Track B may append to**:
- `frontend/src/lib/api.ts` — append `deleteSchedule(id)` and
  `runScheduleNow()` near the existing `addSchedule`/`toggleSchedule` in
  the scheduler section. Do NOT edit the tasks section.
- `src/media_tools/api/routers/scheduler.py` — optionally add a
  `last_run_time` column + APScheduler listener that updates it on job
  completion. Use `_ensure_column` migration. This is the only allowed
  backend touch for Track B; everything else already exists.

**Files Track B must NOT touch** (Track A or shared hot files):
- `src/media_tools/api/routers/tasks.py`
- `frontend/src/pages/Inbox.tsx`
- `frontend/src/pages/Creators.tsx` *(except a one-line replacement of the
  hardcoded toggle with a link pointing at the new Settings section —
  coordinate in section 4 before doing it)*
- `frontend/src/store/useStore.ts`

**Plan**:
1. **API client**: add `deleteSchedule(id)` and `runScheduleNow()` to
   `lib/api.ts`.
2. **`<ScheduleManager>` component** under
   `frontend/src/components/scheduler/ScheduleManager.tsx`:
   - Lists all schedules with: cron expr, enabled toggle, last run time,
     edit / delete / run-now buttons.
   - "新建定时任务" button opens a small dialog with 3 preset radios
     (每天 02:00, 每 6 小时, 每周一 03:00) + a custom cron input with
     client-side validation via `cron-parser` (dep add OK).
   - Inline edit of cron on existing rows.
3. **Mount in Settings.tsx**: new top-level section after the account-pool
   blocks, before 全局参数.
4. **Backend (optional, small)**: add `last_run_time` column to
   `scheduled_tasks`; on APScheduler `EVENT_JOB_EXECUTED` listener in
   `startup_scheduler()`, write the timestamp. Include the column in the
   GET response.
5. **Creators.tsx integration**: the existing hardcoded daily-02:00
   toggle should either stay as a shortcut that links to the new
   Settings section, or be removed. Pick the less disruptive. **Note this
   decision in section 4 before merging.**

**Acceptance**:
- `pytest` still 157/157.
- `tsc --noEmit` clean.
- Smoke: create a custom cron schedule, edit it, toggle off, run-now,
  delete. All four return 2xx and UI reflects within 500ms.
- Existing Creators-page toggle still works OR is replaced with a clear
  link to the Settings section.

**Risks**:
- Adding `cron-parser` is ~5KB; acceptable. If you dislike the dep,
  inline-validate via a small regex for common expressions and skip the
  custom free-text mode.
- The APScheduler listener fires inside the scheduler's thread; the DB
  write uses the existing `get_db_connection()` which is thread-safe.

---

## 3. Coordination protocol

| Event | What to do |
|---|---|
| Starting work | `git pull --rebase` on both repos. Read section 4 of this doc for latest cross-session notes. |
| Finished a logical chunk | Commit. Push. Update section 4 with a one-liner. |
| About to edit a shared file (`api.ts`, this doc, `scheduler.py`) | Before editing, `git pull --rebase`. If the other session has appended recently, your diff must stay below theirs, not above. |
| Conflict during rebase | The file you're conflicting on indicates a contract break. Resolve in favor of keeping both additions if they're in different sections; otherwise stop and flag in section 4. |
| You think the plan is wrong | Don't silently change scope. Update section 4 with a proposed change and wait for the other session to read it. |

**Cadence**: aim for a push every 30–60 min of work. Don't let unpushed
commits pile up — the other session can't coordinate against what it can't
see.

---

## 4. Cross-session notes (append-only log)

Format: `YYYY-MM-DD HH:MM [A|B|user] <message>`.

```
2026-04-18 00:45 [setup] doc created; starting state = d07fe53 on main,
                 webui-apple-design on frontend
2026-04-18 01:20 [A] Claiming Track A (task cancellation). Will commit in
                 small chunks: DB migration → asyncio registry refactor →
                 CancelledError handlers → /cancel endpoint → frontend.
                 Session B: Track B files are untouched, go ahead.
```

<!--
Each session appends below. Do not delete entries. Keep it short — if
something needs discussion, open an item and the other session will
reply on the next line.
-->
