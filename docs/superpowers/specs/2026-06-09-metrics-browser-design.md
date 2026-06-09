# Metrics Browser Page — Design Spec

**Date:** 2026-06-09  
**Status:** Approved  
**Route:** `/metrics` (replaces existing table view)

---

## Problem

The current `/metrics` page renders metrics in a flat table. Clicking a row opens a slide-out Sheet from the right edge. This works but doesn't feel like a browsing experience — the Sheet is a temporary overlay, there's no persistent spatial context, and the layout wastes horizontal space.

## Solution

Replace the table+Sheet pattern with a **master-detail split layout** that fills the content area. The left column is a scrollable, filterable list; the right column is a persistent detail panel that updates in place as the user selects different metrics. No Sheet overlays, no navigation, no page reloads.

---

## Layout

```
┌─────────────────────────────────────────────────────────┐
│  PageHeader: "Metrics Registry"         [Create Metric]  │
├──────────────────────┬──────────────────────────────────┤
│  LEFT: List (35%)    │  RIGHT: Detail Panel (65%)       │
│  ┌────────────────┐  │  ┌─────────────────────────────┐ │
│  │ 🔍 Search...   │  │  │ faithfulness_score  AI JUDGE│ │
│  │ [All] [AI] [P] │  │  │ Evaluates factual...        │ │
│  ├────────────────┤  │  │─────────────────────────────│ │
│  │ ▶ faithfulness │  │  │ SCORING SCALE               │ │
│  │   AI JUDGE     │  │  │ [0.0] [1.0] [float]         │ │
│  │   Evaluates... │  │  │─────────────────────────────│ │
│  │                │  │  │ REQUIRED INPUTS             │ │
│  │ latency_ms     │  │  │ {{input_text}} {{context}}  │ │
│  │ PRIMITIVE      │  │  │─────────────────────────────│ │
│  │ Raw latency... │  │  │ MODEL CONFIG                │ │
│  │                │  │  │ gemini-1.5-pro · google     │ │
│  │ context_rel... │  │  │─────────────────────────────│ │
│  │ AI JUDGE       │  │  │ PROMPT TEMPLATE             │ │
│  │ Measures if... │  │  │ You are evaluating...       │ │
│  └────────────────┘  │  │─────────────────────────────│ │
│                      │  │ [Edit in Playground] [Del]  │ │
│                      │  └─────────────────────────────┘ │
└──────────────────────┴──────────────────────────────────┘
```

The layout is full-height (fills `calc(100vh - header)`). Both columns scroll independently.

---

## Components

### `/app/metrics/page.tsx` (server component — updated)

- Fetches `GET /v1/configs/metrics` server-side with `cache: 'no-store'`
- Renders `PageHeader` + `MetricsBrowserClient`
- Removes all Form/search/filter URL param logic (search moves client-side)

### `MetricsBrowserClient` (new client component)

- Holds `selectedId: string | null` in `useState`
- Initializes `selectedId` to the first metric's ID on mount
- Renders the two-column flex layout
- Passes `metrics`, `selectedId`, `onSelect` down to `MetricsList`
- Passes the resolved selected `Metric | null` to `MetricDetail`

### `MetricsList` (new client component)

**Props:** `metrics: Metric[]`, `selectedId: string | null`, `onSelect: (id: string) => void`

**Behavior:**
- Sticky header containing: search input + type filter tabs (`All` / `AI Judge` / `Primitive`)
- Each tab shows a live count badge reflecting the filtered result count
- Search filters by `name` and `description` (case-insensitive, client-side, instant — no debounce needed for ≤30 metrics)
- Type filter applied after search
- Renders filtered metrics as rows
- Empty state: "No metrics match your search."

**Row anatomy (two lines):**
```
faithfulness_score    [AI JUDGE]
Evaluates factual consistency of AI responses...
```
- Line 1: `name` (truncated) + type `Badge`
- Line 2: `description` truncated to 1 line with `text-ellipsis`
- Selected row: left accent border (2px, primary color) + subtle background highlight
- Hover: subtle background transition

### `MetricDetail` (new client component)

**Props:** `metric: Metric | null`

**Behavior:**
- When `metric` is null: renders a centered empty state ("Select a metric to view details")
- When a metric is selected: renders a scrollable panel with sections in this order:

| Section | Condition | Content |
|---|---|---|
| Header | Always | `name` + type `Badge` |
| Description | Always | Full description text |
| Scoring Scale | Always | Min / Max / Type in three small stat widgets |
| Required Inputs | When `required_inputs` present | Variable name chips styled as `{{ var }}` |
| Model Config | `type === "ai-judge"` only | Provider, model, temperature rows |
| Prompt Template | `type === "ai-judge"` only | `<pre>` code block, scrollable up to `max-h-72` |
| Actions | Always | Edit or system-lock button + Delete button |

**Action buttons:**
- AI Judge: "Edit in Playground" → `href="/playground?metric={name}"` + `DeleteMetricButton`
- Primitive: disabled "System metric — read only" button with `Tooltip` explaining it

---

## Data Flow

```
page.tsx (server)
  └─ fetch /v1/configs/metrics → Metric[]
       └─ MetricsBrowserClient (client, owns selectedId state)
            ├─ MetricsList (renders list, calls onSelect on row click)
            └─ MetricDetail (renders full detail for selected metric)
```

- **No client-side fetch.** All data comes from the server component.
- **Delete** uses the existing `DeleteMetricButton` which calls `router.refresh()` after success, causing the server component to re-fetch. If the deleted metric was selected, `MetricsBrowserClient` resets `selectedId` to the first remaining metric.

---

## File Changes

| File | Action |
|---|---|
| `app/metrics/page.tsx` | Update — strip search params logic, render `MetricsBrowserClient` |
| `components/metrics/MetricsBrowserClient.tsx` | Create — client wrapper with `selectedId` state |
| `components/metrics/MetricsList.tsx` | Create — left panel list with search + filter |
| `components/metrics/MetricDetail.tsx` | Create — right panel detail view |
| `components/metrics/MetricsTableClient.tsx` | Delete (or keep file, stop importing it) |

---

## Out of Scope

- Editing metrics inline (goes to Playground)
- Pagination (30 metrics fits in memory fine)
- Persisting selected metric in URL (adds complexity, not needed for browsing)
- Any new API endpoints (all existing endpoints are sufficient)
