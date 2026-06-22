# Real-Time UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate manual page refresh across the eval-platform UI by adding SWR polling (list pages) and SSE push (evaluation detail page).

**Architecture:** List pages (`/evaluations`, `/runtimes`, `/metrics`, `/pipelines`) convert to a hybrid Server Component shell + `"use client"` data component using SWR at 3s intervals. The evaluation detail page adds a `useEvaluationStream` hook that opens an `EventSource` to a new FastAPI SSE endpoint, with SWR polling as fallback.

**Tech Stack:** `swr` (new), `asyncio.Queue` fan-out event bus (new backend), `EventSource` browser API, Next.js 16, FastAPI, React 19

---

## Task 1: Install SWR and create the shared fetcher

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/hooks/use-swr-fetcher.ts`

- [ ] **Step 1: Install SWR**

```bash
cd frontend && npm install swr
```

Expected output: `added 1 package` (swr has no extra deps).

- [ ] **Step 2: Create the shared typed fetcher**

Create `frontend/hooks/use-swr-fetcher.ts`:

```ts
/**
 * Shared SWR fetcher. Throws on non-OK responses so SWR surfaces them as errors.
 */
export async function swrFetcher<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    if (res.status === 404) return [] as unknown as T;
    throw new Error(`Fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add package.json package-lock.json hooks/use-swr-fetcher.ts
git commit -m "feat: install swr and add shared fetcher hook"
```

---

## Task 2: Backend — per-job event queue fan-out in orchestrator

**Files:**
- Modify: `backend/app/core/eval_engine/services/evaluation_orchestrator.py`
- Test: `backend/tests/core/test_orchestrator_queues.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/core/test_orchestrator_queues.py`:

```python
import asyncio
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from app.core.eval_engine.services.evaluation_orchestrator import EvaluationOrchestratorService
from app.core.eval_engine.models import PipelineRunResult, AssertionStatus, BatchRunStatus


def _make_orchestrator() -> EvaluationOrchestratorService:
    return EvaluationOrchestratorService(
        batch_result_repo=MagicMock(),
        pipeline_eval_srv=MagicMock(),
        runtime_state_repo=MagicMock(),
        dataset_repo=MagicMock(),
        pipeline_repo=MagicMock(),
    )


@pytest.mark.anyio
async def test_subscribe_receives_testcase_result():
    """A queue subscribed before evaluate_testcase completes receives the result."""
    orchestrator = _make_orchestrator()
    job_id = uuid4()

    # Subscribe a queue
    q = await orchestrator.subscribe(job_id)

    # Simulate a result being published
    fake_result = MagicMock(spec=PipelineRunResult)
    await orchestrator.publish_result(job_id, fake_result)

    received = q.get_nowait()
    assert received is fake_result


@pytest.mark.anyio
async def test_publish_sentinel_on_complete_job():
    """publish_sentinel puts None into all queues for the job."""
    orchestrator = _make_orchestrator()
    job_id = uuid4()

    q1 = await orchestrator.subscribe(job_id)
    q2 = await orchestrator.subscribe(job_id)

    await orchestrator.publish_sentinel(job_id)

    assert q1.get_nowait() is None
    assert q2.get_nowait() is None


@pytest.mark.anyio
async def test_unsubscribe_removes_queue():
    """After unsubscribe, publish_result does not enqueue into removed queue."""
    orchestrator = _make_orchestrator()
    job_id = uuid4()

    q = await orchestrator.subscribe(job_id)
    await orchestrator.unsubscribe(job_id, q)

    fake_result = MagicMock(spec=PipelineRunResult)
    await orchestrator.publish_result(job_id, fake_result)

    assert q.empty()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/core/test_orchestrator_queues.py -v
```

Expected: FAIL — `EvaluationOrchestratorService` has no `subscribe`, `publish_result`, `publish_sentinel`, or `unsubscribe` methods.

- [ ] **Step 3: Add the event bus methods to the orchestrator**

In `backend/app/core/eval_engine/services/evaluation_orchestrator.py`, add three class-level attributes and four new methods:

```python
# Add after the existing class-level attributes (_locks, _global_lock):
_subscriber_queues: dict[UUID, list[asyncio.Queue]] = {}
_queues_lock = asyncio.Lock()
```

Add these four methods to `EvaluationOrchestratorService` (after `_get_lock`):

```python
@classmethod
async def subscribe(cls, job_id: UUID) -> asyncio.Queue:
    """Register a new SSE subscriber queue for a job. Returns the queue."""
    q: asyncio.Queue = asyncio.Queue()
    async with cls._queues_lock:
        cls._subscriber_queues.setdefault(job_id, []).append(q)
    return q

@classmethod
async def unsubscribe(cls, job_id: UUID, q: asyncio.Queue) -> None:
    """Remove a subscriber queue, e.g. when the SSE client disconnects."""
    async with cls._queues_lock:
        queues = cls._subscriber_queues.get(job_id, [])
        if q in queues:
            queues.remove(q)

@classmethod
async def publish_result(cls, job_id: UUID, result: 'PipelineRunResult') -> None:
    """Publish a completed PipelineRunResult to all subscribers of a job."""
    async with cls._queues_lock:
        queues = list(cls._subscriber_queues.get(job_id, []))
    for q in queues:
        await q.put(result)

@classmethod
async def publish_sentinel(cls, job_id: UUID) -> None:
    """Signal job completion to all subscribers by putting None into each queue."""
    async with cls._queues_lock:
        queues = list(cls._subscriber_queues.get(job_id, []))
    for q in queues:
        await q.put(None)
```

Also update `evaluate_testcase` to call `publish_result` after saving, and `complete_job` to call `publish_sentinel`. At the end of `evaluate_testcase`, after `self.__batch_result_repo.save(job)` inside the lock block, add:

```python
        await self.publish_result(job_id, result)
```

And at the end of `complete_job`, after `self.__batch_result_repo.save(job)` inside the lock block, add:

```python
            await self.publish_sentinel(job_id)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/core/test_orchestrator_queues.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/core/eval_engine/services/evaluation_orchestrator.py tests/core/test_orchestrator_queues.py
git commit -m "feat: add per-job asyncio.Queue event bus to orchestrator"
```

---

## Task 3: Backend — SSE streaming endpoint

**Files:**
- Modify: `backend/app/api/v1/endpoints/evals.py`
- Test: `backend/tests/api/v1/test_evals_stream.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/api/v1/test_evals_stream.py`:

```python
import json
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.eval_engine.models import (
    PipelineRunResult, AssertionStatus, BatchRunResult, BatchRunStatus
)

client = TestClient(app)


def _make_batch_result(job_id):
    return BatchRunResult(
        job_id=job_id,
        pipeline_id=uuid4(),
        dataset_id=uuid4(),
        status=BatchRunStatus.IN_PROGRESS,
        pipeline_run_results=[],
    )


def test_stream_yields_testcase_complete_then_job_complete():
    """SSE endpoint streams testcase_complete events then closes on job_complete (sentinel)."""
    import asyncio
    job_id = uuid4()
    fake_result = MagicMock(spec=PipelineRunResult)
    fake_result.model_dump.return_value = {"run_id": str(uuid4()), "overall_status": 0}

    # Queue that yields one result then a sentinel
    q = asyncio.Queue()
    q.put_nowait(fake_result)
    q.put_nowait(None)  # sentinel = job complete

    with (
        patch(
            "app.api.v1.endpoints.evals.get_evaluation_orchestrator",
        ) as mock_dep,
        patch(
            "app.core.eval_engine.services.evaluation_orchestrator.EvaluationOrchestratorService.subscribe",
            new_callable=AsyncMock,
            return_value=q,
        ),
        patch(
            "app.core.eval_engine.services.evaluation_orchestrator.EvaluationOrchestratorService.unsubscribe",
            new_callable=AsyncMock,
        ),
    ):
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_job.return_value = _make_batch_result(job_id)
        mock_dep.return_value = mock_orchestrator

        with client.stream("GET", f"/v1/evaluations/{job_id}/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            body = response.read().decode()

        assert "testcase_complete" in body
        assert "job_complete" in body


def test_stream_returns_404_for_unknown_job():
    """SSE endpoint returns 404 if the job does not exist."""
    job_id = uuid4()

    with patch(
        "app.api.v1.endpoints.evals.get_evaluation_orchestrator",
    ) as mock_dep:
        mock_orchestrator = MagicMock()
        from app.core.exceptions import NotFoundError
        mock_orchestrator.get_job.side_effect = NotFoundError("not found")
        mock_dep.return_value = mock_orchestrator

        response = client.get(f"/v1/evaluations/{job_id}/stream")
        assert response.status_code == 404
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/api/v1/test_evals_stream.py -v
```

Expected: FAIL — route `/v1/evaluations/{id}/stream` does not exist.

- [ ] **Step 3: Add the SSE endpoint**

In `backend/app/api/v1/endpoints/evals.py`, add these imports at the top:

```python
import asyncio
import json
from fastapi.responses import StreamingResponse
```

Add this endpoint at the end of the file:

```python
@router.get('/{evaluation_id}/stream')
async def stream_evaluation(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> StreamingResponse:
    """SSE endpoint that streams PipelineRunResult events as testcases complete."""
    from app.core.eval_engine.services.evaluation_orchestrator import EvaluationOrchestratorService as Svc

    # Verify job exists
    try:
        orchestrator.get_job(evaluation_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f'Evaluation {evaluation_id} not found.')

    async def event_generator():
        q = await Svc.subscribe(evaluation_id)
        try:
            while True:
                item = await asyncio.wait_for(q.get(), timeout=30.0)
                if item is None:
                    yield f"event: job_complete\ndata: {json.dumps({'status': 'COMPLETED'})}\n\n"
                    break
                yield f"event: testcase_complete\ndata: {json.dumps(item.model_dump())}\n\n"
        except asyncio.TimeoutError:
            # Keep-alive: no events for 30s, send a comment and loop
            yield ": keep-alive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await Svc.unsubscribe(evaluation_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/api/v1/test_evals_stream.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/api/v1/endpoints/evals.py tests/api/v1/test_evals_stream.py
git commit -m "feat: add SSE streaming endpoint for evaluation results"
```

---

## Task 4: EvaluationsTable client component + update evaluations page

**Files:**
- Create: `frontend/components/evaluations/evaluations-table.tsx`
- Modify: `frontend/app/evaluations/page.tsx`

- [ ] **Step 1: Create the EvaluationsTable client component**

Create `frontend/components/evaluations/evaluations-table.tsx`. This file contains all the table rendering and filter/sort logic extracted from `app/evaluations/page.tsx`, now using `useSWR` and `useSearchParams`:

```tsx
"use client";

import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import { swrFetcher } from "@/hooks/use-swr-fetcher";
import { BatchRunResult, Pipeline } from "@/lib/types";
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { ChevronRight, ArrowUpDown, Loader2 } from "lucide-react";
import { formatDate } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

interface SortableHeaderProps {
  field: string;
  children: React.ReactNode;
  className?: string;
  sort: string;
  order: string;
  q: string;
}

function SortableHeader({ field, children, className, sort, order, q }: SortableHeaderProps) {
  const isActive = sort === field;
  const nextOrder = isActive && order === "desc" ? "asc" : "desc";
  return (
    <TableHead className={className}>
      <Link
        href={{ pathname: "/evaluations", query: { q, sort: field, order: nextOrder } }}
        className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors group select-none font-mono text-[10px] uppercase tracking-wider font-semibold"
      >
        {children}
        <ArrowUpDown className={`h-3 w-3 transition-colors ${isActive ? "text-primary" : "text-muted-foreground/40 group-hover:text-muted-foreground/80"}`} />
      </Link>
    </TableHead>
  );
}

function getPassRate(run: BatchRunResult): number {
  if (run.pass_rate !== undefined) return run.pass_rate;
  if (!run.pipeline_run_results || run.pipeline_run_results.length === 0) return 0;
  const total = run.pipeline_run_results.length;
  const passes = run.pipeline_run_results.filter(
    (r: { overall_status: number | string }) => r.overall_status === 0 || r.overall_status === "PASS"
  ).length;
  return total > 0 ? (passes / total) * 100 : 0;
}

export function EvaluationsTable() {
  const searchParams = useSearchParams();
  const q = searchParams.get("q") || "";
  const sort = searchParams.get("sort") || "created_at";
  const order = searchParams.get("order") || "desc";

  const { data: allRuns = [], isLoading: runsLoading } = useSWR<BatchRunResult[]>(
    `${API_BASE}/evaluations`,
    swrFetcher,
    { refreshInterval: 3000 }
  );
  const { data: pipelines = [] } = useSWR<Pipeline[]>(
    `${API_BASE}/configs/pipelines`,
    swrFetcher,
    { refreshInterval: 10000 }
  );

  const pipelineMap = new Map(pipelines.map((p) => [p.id, p.name]));

  let runs = allRuns.map((run) => ({
    ...run,
    pipeline_name: pipelineMap.get(run.pipeline_id) || run.pipeline_name,
  }));

  if (q) {
    const lowerQ = q.toLowerCase();
    runs = runs.filter(
      (run) =>
        run.job_id.toLowerCase().includes(lowerQ) ||
        run.pipeline_id.toLowerCase().includes(lowerQ) ||
        run.dataset_id.toLowerCase().includes(lowerQ) ||
        run.pipeline_name?.toLowerCase().includes(lowerQ)
    );
  }

  runs.sort((a, b) => {
    let valA: string | number = "";
    let valB: string | number = "";
    if (sort === "created_at") {
      valA = a.created_at ? new Date(a.created_at).getTime() : 0;
      valB = b.created_at ? new Date(b.created_at).getTime() : 0;
    } else if (sort === "pass_rate") {
      valA = getPassRate(a);
      valB = getPassRate(b);
    } else if (sort === "pipeline_name") {
      valA = (a.pipeline_name || a.pipeline_id).toLowerCase();
      valB = (b.pipeline_name || b.pipeline_id).toLowerCase();
    } else if (sort === "status") {
      valA = a.status.toLowerCase();
      valB = b.status.toLowerCase();
    }
    if (valA < valB) return order === "asc" ? -1 : 1;
    if (valA > valB) return order === "asc" ? 1 : -1;
    return 0;
  });

  return (
    <div className="border border-border/40 rounded-[2px] overflow-hidden bg-card/30 backdrop-blur-xs shadow-sm">
      {runsLoading && allRuns.length === 0 ? (
        <div className="flex items-center justify-center h-32 text-muted-foreground gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="font-mono text-xs">Loading evaluations...</span>
        </div>
      ) : (
        <Table>
          <TableHeader className="bg-muted/30 border-b border-border/60">
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="w-[120px] font-mono text-muted-foreground uppercase text-[10px] tracking-widest h-11">Job ID</TableHead>
              <SortableHeader field="pipeline_name" sort={sort} order={order} q={q}>Pipeline</SortableHeader>
              <SortableHeader field="dataset_name" sort={sort} order={order} q={q}>Dataset</SortableHeader>
              <SortableHeader field="status" sort={sort} order={order} q={q}>Status</SortableHeader>
              <SortableHeader field="created_at" className="w-[200px]" sort={sort} order={order} q={q}>Run Time</SortableHeader>
              <SortableHeader field="pass_rate" className="text-right w-36" sort={sort} order={order} q={q}>Pass Rate</SortableHeader>
              <TableHead className="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground h-32 font-mono text-xs italic">
                  No evaluation runs found.
                </TableCell>
              </TableRow>
            ) : (
              runs.map((run) => {
                const pipelineStr = run.pipeline_name || run.pipeline_id.split("-")[0];
                const datasetStr = run.dataset_name || run.dataset_id.split("-")[0];
                const passRate = getPassRate(run);
                const timeStr = formatDate(run.created_at);
                return (
                  <TableRow key={run.job_id} className="group hover:bg-muted/30 border-border/40 transition-colors cursor-pointer relative">
                    <TableCell className="font-mono text-xs font-medium py-3.5">
                      <Link href={`/evaluations/${run.job_id}`} className="absolute inset-0 z-10">
                        <span className="sr-only">View Details</span>
                      </Link>
                      {run.job_id.split("-")[0]}...
                    </TableCell>
                    <TableCell className="py-3.5">
                      <Link href={`/pipelines/${run.pipeline_id}`} className="z-20 relative inline-flex items-center px-2 py-0.5 text-[11px] font-mono rounded-[2px] bg-secondary/50 text-foreground border border-border/30 hover:bg-secondary hover:border-primary/30 transition-colors">
                        {pipelineStr}
                      </Link>
                    </TableCell>
                    <TableCell className="py-3.5">
                      <Link href={`/datasets/${run.dataset_id}`} className="z-20 relative inline-flex items-center px-2 py-0.5 text-[11px] font-mono rounded-[2px] bg-secondary/50 text-muted-foreground border border-border/30 hover:bg-secondary hover:text-foreground hover:border-primary/30 transition-colors">
                        {datasetStr}
                      </Link>
                    </TableCell>
                    <TableCell className="py-3.5">
                      <Badge variant="secondary" className={`rounded-[2px] font-mono text-[9px] font-semibold uppercase ${run.status === "COMPLETED" ? "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border border-emerald-500/20" : run.status === "FAILED" ? "bg-rose-500/10 text-rose-600 hover:bg-rose-500/20 border border-rose-500/20" : "bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 border border-blue-500/20"}`}>
                        {run.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground py-3.5">{timeStr}</TableCell>
                    <TableCell className="text-right py-3.5">
                      {passRate !== undefined ? (
                        <div className="flex items-center justify-end gap-2.5">
                          <div className="w-16 h-1.5 bg-secondary rounded-[1px] overflow-hidden border border-border/20">
                            <div className={`h-full rounded-[1px] ${passRate >= 80 ? "bg-emerald-500" : passRate >= 50 ? "bg-amber-500" : "bg-rose-500"}`} style={{ width: `${passRate}%` }} />
                          </div>
                          <span className="text-xs font-mono font-medium w-8 text-right text-foreground/80">{passRate.toFixed(0)}%</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-xs font-mono">N/A</span>
                      )}
                    </TableCell>
                    <TableCell className="py-3.5">
                      <ChevronRight className="h-4 w-4 text-muted-foreground opacity-50 group-hover:opacity-100 transition-opacity" />
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Replace app/evaluations/page.tsx with a thin shell**

Replace the entire contents of `frontend/app/evaluations/page.tsx`:

```tsx
import { Suspense } from "react";
import Form from "next/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { EvaluationsTable } from "@/components/evaluations/evaluations-table";

export const dynamic = "force-dynamic";

export default async function EvaluationsPage(props: {
  searchParams: Promise<{ q?: string }>;
}) {
  const searchParams = await props.searchParams;
  const q = searchParams.q || "";

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 bg-background">
      <PageHeader
        preTitle="Evaluation Workspace"
        title="Batch Run Logs"
        description="View all recent evaluation batches, execution timestamps, and their overarching pass rates."
      />

      <div className="flex flex-col sm:flex-row gap-4 items-center shrink-0 bg-card/20 p-4 rounded-[2px] border border-border/40">
        <Form action="/evaluations" className="flex w-full max-w-sm gap-2">
          <Input
            name="q"
            defaultValue={q}
            placeholder="Search by ID or name..."
            className="flex-1 rounded-[2px] border-border text-xs font-mono h-9"
          />
          <Button type="submit" variant="secondary" className="rounded-[2px] font-mono text-[10px] uppercase tracking-wider h-9 px-4">
            Search
          </Button>
        </Form>
      </div>

      <Suspense fallback={null}>
        <EvaluationsTable />
      </Suspense>
    </div>
  );
}
```

Note: `<Suspense>` is required because `EvaluationsTable` uses `useSearchParams()`.

- [ ] **Step 3: Verify the page works**

```bash
cd frontend && npm run dev
```

Open http://localhost:3000/evaluations — table should load without manual refresh. Check browser network tab: a new request to `/v1/evaluations` fires every 3s.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add components/evaluations/evaluations-table.tsx app/evaluations/page.tsx
git commit -m "feat: evaluations list auto-refreshes via SWR polling"
```

---

## Task 5: RuntimesLive client component + update runtimes page

**Files:**
- Create: `frontend/components/runtimes/runtimes-live.tsx`
- Modify: `frontend/app/runtimes/page.tsx`

- [ ] **Step 1: Create the RuntimesLive client component**

Create `frontend/components/runtimes/runtimes-live.tsx`. This moves the filter/sort/pagination logic from the server component into the client:

```tsx
"use client";

import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import { swrFetcher } from "@/hooks/use-swr-fetcher";
import { RuntimeState } from "@/lib/types";
import { RuntimeTable } from "@/components/runtimes/runtime-table";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";
const PAGE_SIZE = 12;

export function RuntimesLive() {
  const searchParams = useSearchParams();
  const q = searchParams.get("q") || "";
  const sort = searchParams.get("sort") || "desc";
  const page = parseInt(searchParams.get("page") || "1", 10);

  const { data: runtimes = [] } = useSWR<RuntimeState[]>(
    `${API_BASE}/runtimes`,
    swrFetcher,
    { refreshInterval: 3000 }
  );

  const getFirstEventTime = (events: RuntimeState["events"]) => {
    if (!events || events.length === 0) return 0;
    return Math.min(...events.map((e) => new Date(e.timestamp).getTime()));
  };

  let filtered = runtimes;
  if (q) {
    const qLower = q.toLowerCase();
    filtered = filtered.filter((r) => r.runtime_id.toLowerCase().includes(qLower));
  }

  filtered = [...filtered].sort((a, b) => {
    const aTime = getFirstEventTime(a.events);
    const bTime = getFirstEventTime(b.events);
    return sort === "asc" ? aTime - bTime : bTime - aTime;
  });

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
  const safePage = Math.max(1, Math.min(page, totalPages));
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <RuntimeTable
      data={paginated}
      total={filtered.length}
      page={safePage}
      pageSize={PAGE_SIZE}
      totalPages={totalPages}
      q={q}
      sort={sort}
    />
  );
}
```

- [ ] **Step 2: Replace app/runtimes/page.tsx with a thin shell**

Replace the entire contents of `frontend/app/runtimes/page.tsx`:

```tsx
import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { RuntimesLive } from "@/components/runtimes/runtimes-live";

export default function RuntimesPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 flex flex-col h-[calc(100vh-3.5rem)] bg-background">
      <PageHeader
        preTitle="Telemetry Console"
        title="Execution Runtimes"
        description="Inspect, filter, and analyze the individual execution traces and telemetry from your AI pipelines."
      />

      <div className="border border-border/40 rounded-[2px] bg-card/30 backdrop-blur-xs flex-1 overflow-hidden flex flex-col">
        <Suspense fallback={null}>
          <RuntimesLive />
        </Suspense>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add components/runtimes/runtimes-live.tsx app/runtimes/page.tsx
git commit -m "feat: runtimes list auto-refreshes via SWR polling"
```

---

## Task 6: SWR polling for Metrics and Pipelines pages

**Files:**
- Modify: `frontend/components/metrics/MetricsBrowserClient.tsx`
- Create: `frontend/components/pipelines/pipelines-grid.tsx`
- Modify: `frontend/app/metrics/page.tsx`
- Modify: `frontend/app/pipelines/page.tsx`

- [ ] **Step 1: Add SWR to MetricsBrowserClient**

Open `frontend/components/metrics/MetricsBrowserClient.tsx`. Find the component's props interface and the `metrics` prop. Add a `useSWR` call at the top of the component body so it fetches its own data, using the passed `metrics` as `fallbackData`. Then remove the fetch from `app/metrics/page.tsx`.

Add to the top of `MetricsBrowserClient.tsx`:

```tsx
import useSWR from "swr";
import { swrFetcher } from "@/hooks/use-swr-fetcher";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";
```

Inside the component, replace usage of the `metrics` prop with:

```tsx
const { data: metrics = [] } = useSWR<Metric[]>(
  `${API_BASE}/configs/metrics`,
  swrFetcher,
  { refreshInterval: 5000, fallbackData: [] }
);
```

Remove `metrics` from the component's props interface and anywhere it was previously passed in.

- [ ] **Step 2: Simplify app/metrics/page.tsx**

Replace the entire contents of `frontend/app/metrics/page.tsx`:

```tsx
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Settings2 } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { MetricsBrowserClient } from "@/components/metrics/MetricsBrowserClient";

export default function MetricsPage() {
  return (
    <div className="p-8 w-full flex flex-col h-[calc(100vh-3.5rem)] gap-6 bg-background">
      <PageHeader
        preTitle="Evaluation Core"
        title="Metrics Registry"
        description="Browse and manage your primitive and AI-judged evaluation metrics."
        actions={
          <Link href="/metric-builder">
            <Button size="sm" className="h-9 shadow-sm rounded-[2px]">
              <Settings2 className="w-4 h-4 mr-2" />
              Create Custom Metric
            </Button>
          </Link>
        }
      />
      <MetricsBrowserClient />
    </div>
  );
}
```

- [ ] **Step 3: Create PipelinesGrid client component**

Create `frontend/components/pipelines/pipelines-grid.tsx`:

```tsx
"use client";

import useSWR from "swr";
import Link from "next/link";
import { swrFetcher } from "@/hooks/use-swr-fetcher";
import { Pipeline } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ListTree, Plus, Settings2 } from "lucide-react";
import { PipelineCardMenu } from "@/components/pipelines/PipelineCardMenu";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export function PipelinesGrid() {
  const { data: pipelines = [] } = useSWR<Pipeline[]>(
    `${API_BASE}/configs/pipelines`,
    swrFetcher,
    { refreshInterval: 5000 }
  );

  if (pipelines.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-16 border border-dashed border-border/40 rounded-[2px] bg-card/10">
        <div className="w-14 h-14 rounded-full bg-muted/50 flex items-center justify-center mb-4">
          <ListTree className="w-7 h-7 text-muted-foreground opacity-60" />
        </div>
        <h3 className="text-base font-semibold">No pipelines yet</h3>
        <p className="text-sm text-muted-foreground mt-1.5 mb-6 text-center max-w-sm leading-relaxed">
          Create your first observability pipeline to start evaluating traces and tracking semantic thresholds over time.
        </p>
        <Link href="/pipelines/new">
          <Button size="sm" className="rounded-[2px] gap-2">
            <Plus className="w-4 h-4" />
            Create your first pipeline
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {pipelines.map((pipeline, index) => {
        const metricCount = pipeline.metrics?.length || 0;
        return (
          <Card
            key={`${pipeline.id || pipeline.name}-${index}`}
            className="hover:border-primary/30 transition-colors bg-card/30 border-border/40 rounded-[2px] shadow-sm group relative overflow-hidden"
          >
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary/0 group-hover:bg-primary/40 transition-colors rounded-l-[2px]" />
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-3">
                <Link href={`/pipelines/${pipeline.id || pipeline.name}`} className="flex-1 min-w-0">
                  <CardTitle className="group-hover:text-primary transition-colors text-base flex items-center gap-2 truncate">
                    <Settings2 className="w-4 h-4 text-muted-foreground shrink-0 opacity-60" />
                    <span className="truncate">{pipeline.name}</span>
                  </CardTitle>
                </Link>
                <PipelineCardMenu pipelineId={pipeline.id} pipelineName={pipeline.name} />
              </div>
              <div className="flex items-center gap-2 mt-2 ml-6">
                {metricCount === 0 ? (
                  <Badge variant="outline" className="text-[10px] font-mono rounded-[2px] text-amber-500 border-amber-500/30 bg-amber-500/5">
                    No metrics configured
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-[10px] font-mono rounded-[2px] text-emerald-600 border-emerald-500/30 bg-emerald-500/5">
                    {metricCount} metric{metricCount !== 1 ? "s" : ""} configured
                  </Badge>
                )}
              </div>
              <CardDescription className="ml-6 text-xs mt-1">
                Click to configure metrics and thresholds
              </CardDescription>
            </CardHeader>
          </Card>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Replace app/pipelines/page.tsx with a thin shell**

Replace the entire contents of `frontend/app/pipelines/page.tsx`:

```tsx
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { PipelinesGrid } from "@/components/pipelines/pipelines-grid";

export default function PipelinesPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 bg-background">
      <PageHeader
        preTitle="Evaluation Core"
        title="Observability Pipelines"
        description="Configure automated evaluation rulesets and thresholds."
        actions={
          <Link href="/pipelines/new">
            <Button size="sm" className="h-9 rounded-[2px] shadow-sm">
              <Plus className="w-4 h-4 mr-2" />
              New Pipeline
            </Button>
          </Link>
        }
      />
      <PipelinesGrid />
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd frontend && git add components/metrics/MetricsBrowserClient.tsx app/metrics/page.tsx components/pipelines/pipelines-grid.tsx app/pipelines/page.tsx
git commit -m "feat: metrics and pipelines auto-refresh via SWR polling"
```

---

## Task 7: SSE hook + wire into EvaluationDetailsClient

**Files:**
- Create: `frontend/hooks/use-evaluation-stream.ts`
- Modify: `frontend/components/evaluations/evaluation-details-client.tsx`

- [ ] **Step 1: Create the useEvaluationStream hook**

Create `frontend/hooks/use-evaluation-stream.ts`:

```ts
"use client";

import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { swrFetcher } from "@/hooks/use-swr-fetcher";
import { PipelineRunResult } from "@/lib/api/evaluations";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export function useEvaluationStream(
  evaluationId: string,
  initialPipelines: PipelineRunResult[]
) {
  const [pipelines, setPipelines] = useState<PipelineRunResult[]>(initialPipelines);
  const [isComplete, setIsComplete] = useState(false);
  const [useFallback, setUseFallback] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  // SSE path
  useEffect(() => {
    if (isComplete) return;

    const es = new EventSource(`${API_BASE}/evaluations/${evaluationId}/stream`);
    esRef.current = es;

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
      setUseFallback(true);
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [evaluationId, isComplete]);

  // SWR fallback — only activates if SSE failed
  const { data: fallbackPipelines } = useSWR<PipelineRunResult[]>(
    useFallback && !isComplete ? `${API_BASE}/evaluations/${evaluationId}/pipelines` : null,
    swrFetcher,
    { refreshInterval: 5000 }
  );

  useEffect(() => {
    if (fallbackPipelines) {
      setPipelines(fallbackPipelines);
    }
  }, [fallbackPipelines]);

  return { pipelines, isComplete };
}
```

- [ ] **Step 2: Wire the hook into EvaluationDetailsClient**

Open `frontend/components/evaluations/evaluation-details-client.tsx`. Find where `pipelines` is currently defined (likely from a prop). Replace the prop-based `pipelines` state with a call to `useEvaluationStream`.

Add the import at the top of the file:

```tsx
import { useEvaluationStream } from "@/hooks/use-evaluation-stream";
```

Find the component signature. It currently receives `pipelines` and `summary` as props:

```tsx
// BEFORE — find this pattern in the file
export function EvaluationDetailsClient({ summary, pipelines, dataset, runtimes }) {
```

Replace with:

```tsx
// AFTER
export function EvaluationDetailsClient({ summary, dataset, runtimes }) {
  const { pipelines, isComplete } = useEvaluationStream(summary.job_id, []);
```

Remove `pipelines` from the props interface/type definition. The component will now receive live data from the hook instead of the initial server-fetched prop.

Also update `frontend/app/evaluations/[id]/page.tsx` — remove `pipelines` from the `<EvaluationDetailsClient>` props (since the component no longer accepts it):

```tsx
// BEFORE
<EvaluationDetailsClient
  summary={summary}
  pipelines={pipelines}
  dataset={dataset}
  runtimes={runtimes}
/>

// AFTER
<EvaluationDetailsClient
  summary={summary}
  dataset={dataset}
  runtimes={runtimes}
/>
```

- [ ] **Step 3: Verify SSE works end-to-end**

Start backend and frontend:

```bash
# terminal 1
cd backend && uvicorn app.main:app --reload

# terminal 2
cd frontend && npm run dev
```

Trigger an evaluation run via the SDK. Open the evaluation detail page. Open browser DevTools → Network tab → filter by "stream". You should see an open `EventSource` connection to `/v1/evaluations/{id}/stream`. As testcases complete, rows appear in the table without refreshing.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add hooks/use-evaluation-stream.ts components/evaluations/evaluation-details-client.tsx app/evaluations/\[id\]/page.tsx
git commit -m "feat: evaluation detail streams live results via SSE with SWR fallback"
```

---

## Spec Coverage Check

| Spec requirement | Task |
|---|---|
| Evaluations list auto-updates within ~3s | Task 4 |
| Evaluation detail shows results within ~1s | Task 7 |
| Runtimes list auto-updates within ~3s | Task 5 |
| Navigate away stops all fetching/streaming | Tasks 4, 5, 6, 7 (useEffect cleanup / SWR tab-hidden pause) |
| SSE falls back to polling on error | Task 7 |
| No backend changes for SWR pages | Tasks 4, 5, 6 |
| SSE endpoint streams PipelineRunResult events | Task 3 |
| Event bus publishes on evaluate_testcase | Task 2 |
| Sentinel published on complete_job | Task 2 |
