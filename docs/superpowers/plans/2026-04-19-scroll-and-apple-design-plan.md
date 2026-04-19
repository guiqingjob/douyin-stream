# Media Tools Scroll + Apple Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Goal:** Fix scroll by enforcing a single main scroll container, then apply Apple Design tokens (colors + radius first).
>
> **Architecture:** The app runs in a full-height flex shell. Sidebar remains independently scrollable. Main area is `flex-col` with a fixed 48px header and a single `flex-1 overflow-auto` content wrapper hosting `<Outlet />`. Pages must not set root overflow/height. Inbox virtual list scrolls via `customScrollParent`.
>
> **Tech Stack:** React + React Router, Tailwind CSS, react-virtuoso, Vite.

---

## File Map

**Modify**
- `/Users/gq/Projects/media-tools/frontend/src/index.css` (global height + overflow lock, Apple tokens groundwork)
- `/Users/gq/Projects/media-tools/frontend/src/components/layout/AppLayout.tsx` (single scroll container + header + sidebar wrapper)
- `/Users/gq/Projects/media-tools/frontend/src/pages/Creators.tsx` (remove root overflow/height constraints)
- `/Users/gq/Projects/media-tools/frontend/src/pages/Discovery.tsx` (remove root overflow/height constraints)
- `/Users/gq/Projects/media-tools/frontend/src/pages/Settings.tsx` (remove root overflow/height constraints)
- `/Users/gq/Projects/media-tools/frontend/src/pages/Inbox.tsx` (remove internal main scroll, bind Virtuoso to parent scroll)

---

## Task 1: Stage 1 — Global Scroll System (P0)

### Step 1.1: Add global `height: 100%` + disable body scroll

**Files:**
- Modify: `/Users/gq/Projects/media-tools/frontend/src/index.css`

- [ ] Add:
  - `html, body, #root { height: 100%; }`
  - `body { overflow: hidden; }`
- [ ] Run dev server and verify: body has no scrollbars.

### Step 1.2: Implement AppLayout fixed shell + single main scroll container

**Files:**
- Modify: `/Users/gq/Projects/media-tools/frontend/src/components/layout/AppLayout.tsx`

- [ ] Wrap Sidebar with an `aside` that is `w-[220px] h-full overflow-y-auto flex-shrink-0 ...`
- [ ] Set root container: `flex h-full w-full bg-[#F5F5F7] overflow-hidden`
- [ ] Main container: `flex-1 flex flex-col h-full overflow-hidden min-w-0`
- [ ] Add header (48px): `header.h-12.flex-shrink-0 ...`
- [ ] Add content wrapper (唯一滚动容器): `div.flex-1.overflow-auto.p-6` hosting `<Outlet />`

### Step 1.3: Enforce page root constraints (no root overflow/height)

**Files:**
- Modify: `/Users/gq/Projects/media-tools/frontend/src/pages/Creators.tsx`
- Modify: `/Users/gq/Projects/media-tools/frontend/src/pages/Discovery.tsx`
- Modify: `/Users/gq/Projects/media-tools/frontend/src/pages/Settings.tsx`
- Modify: `/Users/gq/Projects/media-tools/frontend/src/pages/Inbox.tsx`

- [ ] Remove root-level `overflow-*` and `h-full/h-screen/min-h-screen` usage.
- [ ] Keep internal component-level `overflow-hidden` that is strictly for visual clipping (e.g., rounded media thumbnails).

### Step 1.4: Inbox — remove internal scroll + Virtuoso bind to parent scroll

**Files:**
- Modify: `/Users/gq/Projects/media-tools/frontend/src/pages/Inbox.tsx`

- [ ] Identify the previous list scroll container (`overflow-y-auto`) and remove it.
- [ ] Bind Virtuoso/VirtuosoGrid to the AppLayout scroll container via `customScrollParent`.
  - Implement a small helper: locate the parent scroll container using a stable selector (e.g., `data-scroll-container="main"` set in AppLayout) and pass it to Virtuoso once available.
- [ ] Ensure no nested scrollbars in Inbox; only the main content wrapper shows scrollbar.

### Step 1.5: Verification (Stage 1)

- [ ] Creators: create enough creators/cards (or use existing dataset) and confirm only main content scrolls; sidebar stays fixed.
- [ ] DevTools computed height: main scroll container has a concrete px height (not `auto`).
- [ ] Settings/Discovery: also scroll correctly, no body scroll.
- [ ] Inbox: scrolling moves content, no nested scrollbars, virtual list still renders and can be interacted with.

---

## Task 2: Stage 2 — Apple Design (P1) — Color + Radius Pass

### Step 2.1: Background + base text colors

**Files:**
- Modify: `/Users/gq/Projects/media-tools/frontend/src/components/layout/AppLayout.tsx`
- Modify: `/Users/gq/Projects/media-tools/frontend/src/index.css` (only if needed to align base colors)

- [ ] App background: `bg-[#F5F5F7]`
- [ ] Default text colors align with `#1D1D1F` / `#86868B` usage where appropriate (page headers already follow this pattern in many places).

### Step 2.2: Radius normalization (limited scope first)

**Files:**
- Modify: targeted UI components and pages after grepping usage

- [ ] Replace `rounded-full` for avatars with `rounded-[10px]`
- [ ] Replace `rounded-2xl` / over-rounded elements according to the spec
- [ ] Avoid introducing Tailwind default heavy shadows (`shadow-md/shadow-lg`)

### Step 2.3: Verification (Stage 2)

- [ ] Visual check: background + key surfaces match Apple palette; no unexpected saturated blues/purples.
- [ ] Compare screenshots before/after for AppLayout shell + Creators + Settings.

