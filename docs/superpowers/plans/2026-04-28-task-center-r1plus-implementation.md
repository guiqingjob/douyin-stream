# Task Center R1+ (macOS Activity Row + Drawer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将任务中心的展示升级为 R1+：默认“macOS Activity 列表行（剩余工作量优先）”，点击展开抽屉查看细节（五段 pipeline、导出目标、失败提示、子任务列表），并保持现有任务行为与数据结构（`payload.pipeline_progress`）不变。

**Architecture:** 前端将 TaskItem 拆为 `Row` + `Drawer` 两种密度层级。Row 只展示主指标（剩余条数、当前阶段、主进度条、关键操作）；Drawer 展示详细信息。后端无需改动（已提供 `pipeline_progress`），仅确保 UI 对缺失字段有稳健降级。

**Tech Stack:** React + Tailwind + shadcn/ui (Badge 等) + Vitest + existing task payload contract

---

## File Map

**Frontend**
- Modify: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx`
- Modify: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx`
- (Optional) Create: `frontend/src/components/layout/TaskMonitorPanel/task-item/R1Row.tsx`
- (Optional) Create: `frontend/src/components/layout/TaskMonitorPanel/task-item/R1Drawer.tsx`
- Modify: `frontend/src/lib/task-utils.ts` (仅当需要新增 label 映射)
- Modify: `frontend/src/types/index.ts` (仅当需要补充 `pipeline_progress` 类型字段)

**Docs (non-prod)**
- Keep updated: `docs/ui/task-center-mockups.html` (R1+ 作为对照稿)

---

## UI Contract (R1+)

### Row (collapsed)
- 左：任务名称（taskTypeLabel）、状态（运行/失败/成功）
- 中：阶段文本（由 `pipeline_progress.stage` 映射），主进度（done/total）
- 中：**剩余 X 条**，其中 `X = max(total - done, 0)`，以 download 计数为默认口径
- 下：细进度条（高度 4~6px，系统灰 track + 系统蓝 fill）
- 右：操作按钮（停止 / 删除记录），危险操作与其它按钮间距 ≥ 16px
- 右：展开/收起箭头（复用已有 Chevron）

### Drawer (expanded)
- 顶部：大数字 + 分母（done / total），并突出“剩余”
- 次级：缺失（audit.missing）、转写进度（transcribe）、导出（export 1/1 + file + status）
- 中部：五段 pipeline（列表/对账/下载/转写/导出）
- 底部：导出目标卡片（文件名 + 状态点）
- 底部：子任务列表（沿用现有 `TaskSubtasks`）

### Stage mapping (must be stable)
`list -> 获取列表`
`audit -> 对账`
`download -> 下载中`
`upload -> 上传中`
`transcribe -> 转写中`
`export -> 导出中`
`done -> 完成`
`failed -> 失败`

---

## Task 1: Refactor TaskItem into Row + Drawer (no behavior changes)

**Files:**
- Modify: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx`
- Test: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx`

- [ ] **Step 1: Write failing test (Row shows remaining workload)**

Add a new test:

```tsx
import { render, screen } from '@testing-library/react'
import { TaskItem } from './TaskItem'
import { vi } from 'vitest'

test('R1+ row shows remaining workload from pipeline_progress.download', () => {
  render(
    <TaskItem
      task={{
        task_id: 't-remain',
        task_type: 'creator_sync_full',
        status: 'RUNNING',
        progress: 0.4,
        payload: JSON.stringify({
          pipeline_progress: {
            stage: 'download',
            download: { done: 12, total: 58 },
            audit: { missing: 1 },
            export: { done: 0, total: 1, file: 'out.docx', status: 'pending' },
          },
        }),
        error_msg: '',
        update_time: new Date().toISOString(),
      }}
      onRetry={vi.fn()}
      isExpanded={false}
      onToggleExpand={vi.fn()}
    />
  )

  expect(screen.getByText('剩余 46 条')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm exec vitest run frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx
```
Expected: FAIL (暂无“剩余 46 条”展示)

- [ ] **Step 3: Implement minimal Row UI**

In `TaskItem.tsx`:
- Add `getRemainingCount(pp)`:
  - Prefer `pp.download` if exists and total>0
  - Else fallback `0`
- In collapsed row, render text `剩余 {remaining} 条`
- Keep existing expand toggle behavior (`isExpanded` + `onToggleExpand`)
- Ensure existing controls continue to render (stop/delete/retry)

- [ ] **Step 4: Run test to verify it passes**

Run same vitest command; Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx
git commit -m "feat(ui): task center R1+ row shows remaining workload"
```

---

## Task 2: Drawer layout (pipeline + export card + consistent system gray)

**Files:**
- Modify: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx`
- Test: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx`

- [ ] **Step 1: Write failing test (Drawer shows export meta)**

```tsx
test('R1+ drawer shows export file and status', () => {
  render(
    <TaskItem
      task={{
        task_id: 't-export',
        task_type: 'pipeline',
        status: 'RUNNING',
        progress: 0.9,
        payload: JSON.stringify({
          pipeline_progress: {
            stage: 'export',
            list: { done: 58, total: 58 },
            audit: { missing: 1 },
            download: { done: 58, total: 58 },
            transcribe: { done: 58, total: 58 },
            export: { done: 0, total: 1, file: 'foo.docx', status: 'writing' },
          },
        }),
        error_msg: '',
        update_time: new Date().toISOString(),
      }}
      onRetry={vi.fn()}
      isExpanded={true}
      onToggleExpand={vi.fn()}
    />
  )

  expect(screen.getByText('导出目标')).toBeInTheDocument()
  expect(screen.getByText('foo.docx')).toBeInTheDocument()
  expect(screen.getByText('写入中')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm exec vitest run frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx
```
Expected: FAIL

- [ ] **Step 3: Implement Drawer blocks**

In `TaskItem.tsx` expanded area:
- Add “导出目标卡片”区块（文件名 + 状态点 + 状态文案）
- Add 5-stage pipeline (use existing `PipelineStep` but render only in expanded)
- Keep `TaskSubtasks` below
- Ensure colors use system gray (`#3C3C43` opacities) and 0.5px separators

- [ ] **Step 4: Run tests (vitest + build + lint)**

```bash
cd frontend
npm exec vitest run
npm run build
npm run lint
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx
git commit -m "feat(ui): task center R1+ drawer shows pipeline and export details"
```

---

## Task 3: Final polish + regression safety

**Files:**
- Modify: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx`
- Test: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx`

- [ ] **Step 1: Add fallback tests (no pipeline_progress)**

```tsx
test('falls back to legacy progress when pipeline_progress missing', () => {
  render(
    <TaskItem
      task={{
        task_id: 't-legacy',
        task_type: 'pipeline',
        status: 'RUNNING',
        progress: 0.25,
        payload: JSON.stringify({ msg: 'x' }),
        error_msg: '',
        update_time: new Date().toISOString(),
      }}
      onRetry={vi.fn()}
      isExpanded={false}
      onToggleExpand={vi.fn()}
    />
  )
  expect(screen.getByText('x')).toBeInTheDocument()
  expect(screen.getByText('25%')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails then implement minimal fallback**
- [ ] **Step 3: Verify full frontend suite**
- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx frontend/src/components/layout/TaskMonitorPanel/TaskItem.test.tsx
git commit -m "test(ui): cover legacy fallback for task center"
```

---

## Verification Checklist
- [ ] Collapsed row shows “剩余 X 条” for download tasks
- [ ] Expanded drawer shows export 1/1 + file + status
- [ ] Pipeline steps render in drawer only
- [ ] No 0/0 shown; missing totals display “--”
- [ ] `vitest`, `build`, `lint` all pass

---

## Execution Choice

Plan complete and saved to:
- `docs/superpowers/plans/2026-04-28-task-center-r1plus-implementation.md`

Two execution options:
1) **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task and review between tasks
2) **Inline Execution** — Execute tasks in this session with checkpoints

Which approach?

