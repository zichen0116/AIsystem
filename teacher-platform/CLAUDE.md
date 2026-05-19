# CLAUDE.md

This file provides guidance to Agents when working with code in this repository.

## Project Overview

Vue 3 + Vite frontend for the multimodal AI teaching platform. Pairs with the FastAPI backend in `../backend/`. Major features: lesson prep (PPT / lesson plans / animations / knowledge graph / mindmap / data analysis), courseware management, knowledge base RAG, question generation, classroom rehearsal player, digital human assistant, and admin dashboard.

## Common Commands

```bash
npm install                              # install dependencies
npm run dev                              # vite dev server (default :5173)
npm run build                            # production build → dist/
npm run preview                          # preview built bundle
npm run test                             # vitest single run
npm run test:watch                       # vitest in watch mode
npx vitest run src/api/http.spec.js      # one test file
npx vitest run -t "buildApiUrl"          # filter by name
```

The dev server expects the backend on `http://localhost:8000`. The Vite proxy (see `vite.config.js`) forwards `/api`, `/media`, `/vmss` (iFlytek digital human), and `/individuation` to the appropriate hosts — never use absolute backend URLs in code; always hit relative paths so the proxy applies.

## Architecture

### Bootstrap & global plugins

`src/main.js` mounts the app with **Pinia**, **Vue Router**, **Element Plus** (locale: zh-CN), and **@kjgl77/datav-vue3**. Global styles live in `src/style.css`. The `@` alias resolves to `src/`.

### Routing & auth gate

`src/router/index.js` uses `createWebHistory` and lazy-loads every view. Routes with `meta.requiresAuth` are gated by a single `beforeEach` hook that:

1. On the very first navigation, calls `userStore.fetchUser()` if a token exists in localStorage — this rehydrates `userInfo` before the guard decides.
2. Redirects unauthenticated users to `/login?redirect=<original>`.

Routes with `meta.layout === 'nav'` render inside `LayoutWithNav` (sidebar + top nav); all others render bare. `App.vue` picks the layout via a computed component.

### API layer

`src/api/http.js` is the single source of truth for HTTP. Use it instead of raw `fetch`:

- `apiRequest(path, opts)` — JSON-in/JSON-out, throws on non-2xx with parsed `detail`.
- `authFetch(path, opts)` — raw `Response` (for streaming / SSE / file downloads).
- `buildApiUrl` / `resolveApiUrl` — respect `VITE_API_BASE` (default `/api` in dev → proxied; absolute URL in prod).
- Both auto-attach `Authorization: Bearer <token>` from localStorage. On `401` outside auth endpoints, they clear the token and redirect to `/login` — do **not** add your own 401 handling.

Feature-specific API modules (`courseware.js`, `ppt.js`, `rehearsal.js`, `download.js`) sit on top and export named functions. `ppt.js` also exposes `streamEvents(url, opts)` — a SSE async-generator using `authFetch` — for all PPT generation streams.

### State (Pinia)

Stores in `src/stores/`:

- `user.js` — auth, 2FA, profile updates, token lifecycle (single source for login state).
- `ppt.js` — PPT project + chat + intent state machine. Imports helpers from `@/utils/pptIntent.js` (intent phase resolution) and `@/utils/pptPlanningContext.js`.
- `courseware.js`, `knowledge.js`, `rehearsal.js`, `adminDigitalHuman.js` — feature-scoped.

Components import stores directly; do not pass store data through props more than one level — re-import in the child.

### View structure

- `src/views/LessonPrep.vue` is the備课中心 shell that switches between tabs (PPT / lesson plan / animation / knowledge / mindmap / data) and mounts the corresponding view, keyed by `resetKeys` so a tab can be force-remounted.
- Each lesson-prep tab is a top-level view (`LessonPrepPpt`, `LessonPlanPage`, etc).
- `src/views/ppt/` is a self-contained PPT-generation flow (`PptIndex` → `PptHome` → `PptDialog` → `PptDescription` → `PptOutline` → `PptPreview`, plus `PptHistory`).
- `src/views/admin/` holds admin-only views, gated by `userStore.userInfo?.is_admin` in `LayoutWithNav`.
- `src/views/rehearsal/` holds the rehearsal lab / new / playback screens; the playback engine and effects are composables (`usePlaybackEngine`, `rehearsalPlaybackEffects`).

### Components

- `src/components/lesson-plan-v2/` — TipTap-based lesson plan writer (chat + editor + sidebar + floating toolbars).
- `src/components/knowledge-graph/` — graph search/filter UI (paired with `useKnowledgeGraph` composable and 3d-force-graph / dagre).
- `src/components/rehearsal/` — slide/laser/spotlight/subtitle overlays for the player.
- `src/components/BigScreen/` — admin data-screen widgets built with datav-vue3 + ECharts.
- `src/components/DigitalHumanAssistant.vue` — floating iFlytek avatar; uses the SDK in `src/libs/avatar-sdk-web_3.1.2.1002/`.

### Heavy libraries (loaded only where used)

- TipTap (rich text) — lesson plan writer only
- ECharts + datav-vue3 — admin dashboards
- 3d-force-graph + three.js — knowledge graph view
- @vue-flow — mindmap editor
- markmap-lib / markmap-view — markmap renderer
- html2pdf.js, html-to-image, @resvg/resvg-wasm — exports
- lottie-web — animations

Keep heavy imports inside their views or `defineAsyncComponent` to preserve route-level code splitting.

## Testing

Vitest with jsdom (`src/test/setup.js` polyfills `scrollY`, `innerHeight`, `scrollTo`). Co-located `*.spec.js` / `*.test.js` next to source. `@vue/test-utils` is available for component tests. Run a focused spec before pushing, then the full suite.

## Conventions

- Components in `PascalCase.vue`, composables as `useXxx.js`, stores in camelCase.
- Use the `@/` alias for any cross-directory import (`@/api/http`, `@/utils/pptIntent`).
- All backend calls go through `apiRequest` / `authFetch` — never construct an absolute URL or attach the auth header manually.
- Element Plus is the default UI kit; prefer its components over hand-rolled equivalents.
- Vue SFC order: `<script setup>` first, then `<template>`, then `<style scoped>` (matches the existing codebase).
