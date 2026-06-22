# Real-Time UI Design Spec

**Date:** 2026-06-22  
**Status:** Approved  
**Scope:** Frontend live data updates — eliminating manual page refresh

---

## Problem

All pages in the eval-platform UI currently use Next.js Server Components that fetch data once at render time. Users must manually refresh the browser to see:
- New evaluation runs appearing in the list
- Evaluation status changing from `RUNNING` → `COMPLETED`
- Testcase results filling in as the SDK submits them
- New runtime sessions appearing
- Updated metrics/pipeline configs

The SDK submits testcases via HTTP to the backend API, so the server always knows the moment state changes. This is the ideal setup for push-based updates.

---

## Approach

Two complementary strategies applied to different page types:

### Path A: SWR Polling — List Pages

**Pages:** `/evaluations`, `/runtimes`, `/metrics`, `/pipelines`

Convert each page from a pure Server Component to a **hybrid**: the Server Component shell handles page chrome (header, URL params, back links), while a new `"use client"` component owns the data via `useSWR` with a 3-second refresh interval.

- No backend changes required
- SWR deduplicates requests and pauses polling when the browser tab is hidden
- The existing fetch functions in `lib/api/` become SWR fetchers with no changes
- Filtering and sorting logic currently on the server moves to the client (same logic, same data shape)

### Path B: SSE Push — Evaluation Detail

**Page:** `/evaluations/[id]`

The evaluation detail page (`EvaluationDetailsClient`) is where users actively watch results fill in. Each testcase result that arrives is a meaningful event. SWR polling at 3s would feel sluggish here.

Instead, a persistent `EventSource` connection streams `PipelineRunResult` events from the backend as each testcase completes. A `useEvaluationStream` hook merges incoming events into the component's local state. If SSE fails (network drop, unsupported proxy), the hook falls back to SWR polling at 5s.

---

## Backend Changes

### New SSE Endpoint

```
GET /v1/evaluations/{evaluation_id}/stream
Content-Type: text/event-stream
```

Streams two event types:
```
event: testcase_complete
data: { ...PipelineRunResult }

event: job_complete
data: { "status": "COMPLETED" | "FAILED" }
```

The endpoint holds the connection open and yields events as they arrive. When the job reaches a terminal state (`COMPLETED` or `FAILED`), it sends `job_complete` and closes the stream.

### Event Bus in Orchestrator

`EvaluationOrchestratorService` gets a per-job `asyncio.Queue[PipelineRunResult | None]`:
- Created when a job is created (`create_job`)
- Written to at the end of `evaluate_testcase` — pushes the `PipelineRunResult`
- Written `None` (sentinel) when `complete_job` is called
- The SSE endpoint `await`s from this queue and yields events
- Queue is cleaned up after the SSE connection closes or the sentinel is consumed

Multiple SSE connections to the same job each get their own queue (fan-out via a list of queues per job).

---

## Frontend Changes

### New Files

| File | Purpose |
|---|---|
| `hooks/use-swr-fetcher.ts` | Typed SWR fetcher — wraps `fetch` and throws on non-OK responses |
| `hooks/use-evaluation-stream.ts` | SSE hook — manages `EventSource` lifecycle, patches state, falls back to polling |
| `components/evaluations/evaluations-table.tsx` | `"use client"` — owns `useSWR` for the evaluations list, renders the table |
| `components/runtimes/runtimes-live.tsx` | `"use client"` — owns `useSWR` for the runtimes list |

### Modified Files

| File | Change |
|---|---|
| `app/evaluations/page.tsx` | Becomes a thin shell; delegates data + rendering to `<EvaluationsTable />` |
| `app/runtimes/page.tsx` | Becomes a thin shell; delegates data + rendering to `<RuntimesLive />` |
| `app/metrics/page.tsx` | Adds `"use client"` + `useSWR` directly (simpler, no extracted component needed) |
| `app/pipelines/page.tsx` | Adds `"use client"` + `useSWR` directly |
| `components/evaluations/evaluation-details-client.tsx` | Adds `useEvaluationStream(evaluationId)` — merges SSE events into `pipelines` state |
| `backend/app/api/v1/endpoints/evals.py` | Adds `GET /{evaluation_id}/stream` SSE endpoint |
| `backend/app/core/eval_engine/services/evaluation_orchestrator.py` | Adds per-job `asyncio.Queue` fan-out event bus |
| `frontend/package.json` | Adds `swr` |

### Hybrid Shell Pattern (Path A)

```tsx
// app/evaluations/page.tsx — Server Component, handles chrome only
export default async function EvaluationsPage(props) {
  const searchParams = await props.searchParams;
  return (
    <div>
      <PageHeader ... />
      <EvaluationsTable initialQ={searchParams.q} />
    </div>
  );
}

// components/evaluations/evaluations-table.tsx — Client Component
"use client";
export function EvaluationsTable({ initialQ }) {
  const { data: runs = [], isLoading } = useSWR("/api/evaluations", fetcher, {
    refreshInterval: 3000,
    fallbackData: [],
  });
  // same filter/sort/render logic as today
}
```

### SSE Hook (Path B)

```tsx
// hooks/use-evaluation-stream.ts
export function useEvaluationStream(evaluationId: string, initialPipelines: PipelineRunResult[]) {
  const [pipelines, setPipelines] = useState(initialPipelines);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    const es = new EventSource(`/v1/evaluations/${evaluationId}/stream`);

    es.addEventListener("testcase_complete", (e) => {
      const result: PipelineRunResult = JSON.parse(e.data);
      setPipelines((prev) => {
        const idx = prev.findIndex((p) => p.run_id === result.run_id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = result;
          return next;
        }
        return [...prev, result];
      });
    });

    es.addEventListener("job_complete", () => {
      setIsComplete(true);
      es.close();
    });

    es.onerror = () => {
      es.close();
      // fallback: SWR polling activates via a separate useSWR with refreshInterval: 5000
    };

    return () => es.close();
  }, [evaluationId]);

  return { pipelines, isComplete };
}
```

---

## UX Behaviour

| Situation | Behaviour |
|---|---|
| Tab in background | SWR pauses `refreshInterval` automatically (`refreshWhenHidden: false` default) |
| SSE connection drops | Hook closes `EventSource`, SWR fallback activates at 5s interval |
| Job reaches COMPLETED | SSE sends `job_complete`, stream closes, SWR polling stops |
| User navigates away | `useEffect` cleanup closes `EventSource` |
| Loading state | SWR `isLoading` — show subtle skeleton or existing empty state |

---

## Out of Scope

- WebSockets (bidirectional — not needed here)
- Real-time updates for dataset pages (data doesn't change after upload)
- Optimistic UI / local mutation (not warranted for this use case)
- Notification toasts on new data (not requested)

---

## Success Criteria

1. Evaluations list auto-updates without any user action within ~3s of a new run being created
2. Evaluation detail page shows each testcase result appearing within ~1s of the SDK submitting it
3. Runtimes list auto-updates within ~3s of a new session appearing
4. Navigating away from a page stops all background fetching/streaming
5. No console errors when SSE falls back to polling
