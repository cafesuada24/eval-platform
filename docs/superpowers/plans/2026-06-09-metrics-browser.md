# Metrics Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat table+Sheet at `/metrics` with a persistent master-detail split layout — scrollable filterable list on the left, full scrollable detail panel on the right.

**Architecture:** Server component fetches all metrics once; a client wrapper holds `selectedId` state and wires the left list to the right detail panel. No new API endpoints, no URL params, no client-side fetching.

**Tech Stack:** Next.js App Router, React, TypeScript, shadcn/ui (`Badge`, `Button`, `Separator`, `Tooltip`), lucide-react, Tailwind CSS.

**Worktree:** `.worktrees/feat-metrics-browser` — branch `feat/metrics-browser`

---

## File Map

| File | Action |
|---|---|
| `frontend/components/metrics/MetricsList.tsx` | **Create** — left panel: search input, type tabs, metric rows |
| `frontend/components/metrics/MetricDetail.tsx` | **Create** — right panel: full scrollable detail view |
| `frontend/components/metrics/MetricsBrowserClient.tsx` | **Create** — client wrapper owning `selectedId` state |
| `frontend/app/metrics/page.tsx` | **Modify** — strip old search-params logic, render `MetricsBrowserClient` |
| `frontend/components/metrics/MetricsTableClient.tsx` | **Delete** (remove import, file can stay on disk) |

---

## Task 1: Create `MetricsList`

**Files:**
- Create: `frontend/components/metrics/MetricsList.tsx`

The left-column component. Accepts the full metrics array and selection state from the parent. Filters locally in response to search and type-tab input.

- [ ] **Step 1: Create the file**

```tsx
"use client"

import { useState, useMemo } from "react"
import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Metric } from "@/lib/types"

type TypeFilter = "all" | "ai-judge" | "primitive"

interface MetricsListProps {
  metrics: Metric[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export function MetricsList({ metrics, selectedId, onSelect }: MetricsListProps) {
  const [query, setQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all")

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return metrics.filter((m) => {
      const matchesQuery =
        !q ||
        m.name.toLowerCase().includes(q) ||
        (m.description && m.description.toLowerCase().includes(q))
      const matchesType = typeFilter === "all" || m.type === typeFilter
      return matchesQuery && matchesType
    })
  }, [metrics, query, typeFilter])

  const aiJudgeCount = useMemo(
    () => metrics.filter((m) => m.type === "ai-judge").length,
    [metrics]
  )
  const primitiveCount = useMemo(
    () => metrics.filter((m) => m.type === "primitive").length,
    [metrics]
  )

  const tabs: { label: string; value: TypeFilter; count: number }[] = [
    { label: "All", value: "all", count: metrics.length },
    { label: "AI Judge", value: "ai-judge", count: aiJudgeCount },
    { label: "Primitive", value: "primitive", count: primitiveCount },
  ]

  return (
    <div className="flex flex-col h-full border-r border-border/40">
      {/* Search + filter header */}
      <div className="p-3 space-y-2 shrink-0 border-b border-border/40 bg-card/20">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search metrics..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-8 h-8 text-xs rounded-[2px] bg-background"
          />
        </div>
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setTypeFilter(tab.value)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-[2px] text-[10px] font-mono transition-colors",
                typeFilter === tab.value
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              {tab.label}
              <span
                className={cn(
                  "text-[9px] px-1 rounded-sm",
                  typeFilter === tab.value
                    ? "bg-primary/20 text-primary"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-xs text-muted-foreground">
            No metrics match your search.
          </div>
        ) : (
          filtered.map((metric) => {
            const isSelected = metric.id === selectedId
            const isAiJudge = metric.type === "ai-judge"
            return (
              <button
                key={metric.id}
                onClick={() => onSelect(metric.id)}
                className={cn(
                  "w-full text-left px-4 py-3 border-b border-border/30 transition-colors",
                  isSelected
                    ? "bg-primary/8 border-l-2 border-l-primary"
                    : "border-l-2 border-l-transparent hover:bg-muted/30"
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span
                    className={cn(
                      "text-xs font-semibold truncate",
                      isSelected ? "text-foreground" : "text-foreground/80"
                    )}
                    title={metric.name}
                  >
                    {metric.name}
                  </span>
                  <Badge
                    variant={isAiJudge ? "default" : "secondary"}
                    className={cn(
                      "text-[9px] rounded-[2px] font-mono shrink-0 px-1.5",
                      isAiJudge ? "bg-primary/10 text-primary border-primary/20" : ""
                    )}
                  >
                    {isAiJudge ? "AI JUDGE" : "PRIMITIVE"}
                  </Badge>
                </div>
                {metric.description && (
                  <p className="text-[10px] text-muted-foreground line-clamp-1 leading-relaxed">
                    {metric.description}
                  </p>
                )}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/metrics/MetricsList.tsx
git commit -m "feat(metrics): add MetricsList left-panel component"
```

---

## Task 2: Create `MetricDetail`

**Files:**
- Create: `frontend/components/metrics/MetricDetail.tsx`

The right-column component. Renders full scrollable detail for a selected metric, or an empty state when nothing is selected.

- [ ] **Step 1: Create the file**

```tsx
"use client"

import Link from "next/link"
import { Pencil, LayoutList } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { DeleteMetricButton } from "@/components/metrics/delete-metric-button"
import { cn } from "@/lib/utils"
import { Metric } from "@/lib/types"

interface MetricDetailProps {
  metric: Metric | null
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
      {children}
    </h4>
  )
}

function StatWidget({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-muted/30 rounded-[2px] p-3 text-center border border-border/30">
      <p className="text-[10px] text-muted-foreground mb-1">{label}</p>
      <p className="text-base font-bold font-mono">{value}</p>
    </div>
  )
}

export function MetricDetail({ metric }: MetricDetailProps) {
  if (!metric) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
        <LayoutList className="w-10 h-10 opacity-20" />
        <p className="text-sm">Select a metric to view details</p>
      </div>
    )
  }

  const isAiJudge = metric.type === "ai-judge"

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-bold tracking-tight">{metric.name}</h2>
            <Badge
              variant={isAiJudge ? "default" : "secondary"}
              className={cn(
                "text-[10px] rounded-[2px] font-mono",
                isAiJudge ? "bg-primary/15 text-primary border-primary/20" : ""
              )}
            >
              {metric.type}
            </Badge>
          </div>
          {metric.description && (
            <p className="text-sm text-muted-foreground leading-relaxed">
              {metric.description}
            </p>
          )}
        </div>

        <Separator className="opacity-40" />

        {/* Scoring Scale */}
        {metric.scoring_scale && (
          <section className="space-y-3">
            <SectionLabel>Scoring Scale</SectionLabel>
            <div className="grid grid-cols-3 gap-3">
              <StatWidget label="Min" value={metric.scoring_scale.min} />
              <StatWidget label="Max" value={metric.scoring_scale.max} />
              <StatWidget label="Type" value={metric.scoring_scale.data_type} />
            </div>
          </section>
        )}

        {/* Required Inputs */}
        {metric.required_inputs && metric.required_inputs.length > 0 && (
          <>
            <Separator className="opacity-40" />
            <section className="space-y-3">
              <SectionLabel>Required Inputs</SectionLabel>
              <div className="flex flex-wrap gap-1.5">
                {metric.required_inputs.map((input) => (
                  <Badge
                    key={input}
                    variant="outline"
                    className="font-mono text-[11px] rounded-[2px]"
                  >
                    {`{{${input}}}`}
                  </Badge>
                ))}
              </div>
            </section>
          </>
        )}

        {/* Model Config (AI Judge only) */}
        {isAiJudge && metric.model_configuration && (
          <>
            <Separator className="opacity-40" />
            <section className="space-y-3">
              <SectionLabel>Model Configuration</SectionLabel>
              <div className="space-y-1.5 text-xs">
                {[
                  { label: "Provider", value: metric.model_configuration.provider },
                  { label: "Model", value: metric.model_configuration.model },
                  { label: "Temperature", value: metric.model_configuration.temperature },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="flex justify-between items-center py-1.5 border-b border-border/30 last:border-0"
                  >
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-mono">{value}</span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}

        {/* Prompt Template (AI Judge only) */}
        {isAiJudge && metric.prompt_template && (
          <>
            <Separator className="opacity-40" />
            <section className="space-y-3">
              <SectionLabel>Prompt Template</SectionLabel>
              <pre className="text-xs font-mono bg-muted/30 p-3 rounded-[2px] whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto border border-border/30">
                {metric.prompt_template}
              </pre>
            </section>
          </>
        )}

        {/* Actions */}
        <Separator className="opacity-40" />
        <div className="flex gap-2">
          {isAiJudge ? (
            <>
              <Link href={`/playground?metric=${metric.name}`} className="flex-1">
                <Button size="sm" className="w-full rounded-[2px] gap-2">
                  <Pencil className="w-3.5 h-3.5" />
                  Edit in Playground
                </Button>
              </Link>
              <DeleteMetricButton metricId={metric.id} metricName={metric.name} />
            </>
          ) : (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex-1">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled
                      className="w-full rounded-[2px] opacity-50 cursor-not-allowed"
                    >
                      System metric — read only
                    </Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Primitive metrics cannot be edited or deleted</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/metrics/MetricDetail.tsx
git commit -m "feat(metrics): add MetricDetail right-panel component"
```

---

## Task 3: Create `MetricsBrowserClient`

**Files:**
- Create: `frontend/components/metrics/MetricsBrowserClient.tsx`

The stateful client wrapper. Owns `selectedId`, wires `MetricsList` to `MetricDetail`, handles post-delete selection reset.

- [ ] **Step 1: Create the file**

```tsx
"use client"

import { useState, useEffect } from "react"
import { MetricsList } from "@/components/metrics/MetricsList"
import { MetricDetail } from "@/components/metrics/MetricDetail"
import { Metric } from "@/lib/types"

interface MetricsBrowserClientProps {
  metrics: Metric[]
}

export function MetricsBrowserClient({ metrics }: MetricsBrowserClientProps) {
  const [selectedId, setSelectedId] = useState<string | null>(
    metrics[0]?.id ?? null
  )

  // When metrics list changes (e.g. after delete), reset selection if the
  // selected metric no longer exists.
  useEffect(() => {
    const stillExists = metrics.some((m) => m.id === selectedId)
    if (!stillExists) {
      setSelectedId(metrics[0]?.id ?? null)
    }
  }, [metrics, selectedId])

  const selectedMetric = metrics.find((m) => m.id === selectedId) ?? null

  return (
    <div className="flex flex-1 min-h-0 border border-border/40 rounded-[2px] bg-card/30 backdrop-blur-xs overflow-hidden">
      <div className="w-[35%] min-w-[280px] shrink-0">
        <MetricsList
          metrics={metrics}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
      </div>
      <div className="flex-1 min-w-0">
        <MetricDetail metric={selectedMetric} />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/metrics/MetricsBrowserClient.tsx
git commit -m "feat(metrics): add MetricsBrowserClient stateful wrapper"
```

---

## Task 4: Update `page.tsx` and wire everything together

**Files:**
- Modify: `frontend/app/metrics/page.tsx`

Replace the old table-based page with the new browser. Remove search-params logic (now client-side). Stop importing `MetricsTableClient`.

- [ ] **Step 1: Replace `page.tsx` content**

```tsx
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Settings2 } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { MetricsBrowserClient } from "@/components/metrics/MetricsBrowserClient";
import { Metric } from "@/lib/types";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getMetrics(): Promise<Metric[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/configs/metrics`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch metrics:", error);
    return [];
  }
}

export default async function MetricsPage() {
  const metrics = await getMetrics();

  return (
    <div className="p-8 max-w-6xl mx-auto flex flex-col h-[calc(100vh-3.5rem)] gap-6 bg-background">
      <PageHeader
        preTitle="Evaluation Core"
        title="Metrics Registry"
        description="Browse and manage your primitive and AI-judged evaluation metrics."
        actions={
          <Link href="/playground">
            <Button size="sm" className="h-9 shadow-sm rounded-[2px]">
              <Settings2 className="w-4 h-4 mr-2" />
              Create Custom Metric
            </Button>
          </Link>
        }
      />
      <MetricsBrowserClient metrics={metrics} />
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Start the dev server and manually verify**

```bash
cd frontend && npm run dev
```

Open http://localhost:3000/metrics. Verify:
- Two-column layout renders
- Left list shows metric name + type badge + description snippet
- Clicking a metric updates the right panel
- Search input filters the list instantly
- Type tabs (All / AI Judge / Primitive) filter correctly with correct counts
- AI Judge metrics show: scoring scale, inputs, model config, prompt, Edit + Delete buttons
- Primitive metrics show: scoring scale, inputs only; "System metric — read only" disabled button
- Deleting a metric refreshes the list and auto-selects the first remaining metric

- [ ] **Step 4: Commit**

```bash
git add frontend/app/metrics/page.tsx
git commit -m "feat(metrics): replace table with master-detail browser layout"
```

---

## Task 5: Cleanup

**Files:**
- `frontend/components/metrics/MetricsTableClient.tsx` — no longer imported

- [ ] **Step 1: Verify `MetricsTableClient` is no longer imported anywhere**

```bash
grep -r "MetricsTableClient" frontend/app frontend/components --include="*.tsx" --include="*.ts"
```

Expected: no results (the file itself can remain on disk — do not delete it, to preserve git history cleanly).

- [ ] **Step 2: Final type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "feat(metrics): metrics browser complete — MetricsTableClient no longer used"
```
