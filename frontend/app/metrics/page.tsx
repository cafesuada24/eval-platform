import Link from "next/link";
import Form from "next/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Settings2, Search, Filter } from "lucide-react";
import { MetricsTableClient } from "@/components/metrics/MetricsTableClient";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

import { Metric } from "@/lib/types";

async function getMetrics(): Promise<Metric[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/configs/metrics`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch metrics:", error);
    return [];
  }
}

import { PageHeader } from "@/components/ui/page-header";

export default async function MetricsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; type?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const q = resolvedSearchParams.q?.toLowerCase() || "";
  const typeFilter = resolvedSearchParams.type || "all";

  let metrics = await getMetrics();

  if (q) {
    metrics = metrics.filter(m =>
      m.name.toLowerCase().includes(q) ||
      (m.description && m.description.toLowerCase().includes(q))
    );
  }

  if (typeFilter !== "all") {
    metrics = metrics.filter(m => m.type === typeFilter);
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 flex flex-col h-[calc(100vh-3.5rem)] bg-background">
      <PageHeader
        preTitle="Evaluation Core"
        title="Metrics Registry"
        description="Manage your primitive and custom AI-judged evaluation metrics."
        actions={
          <Link href="/playground">
            <Button size="sm" className="h-9 shadow-sm rounded-[2px]">
              <Settings2 className="w-4 h-4 mr-2" />
              Create Custom Metric
            </Button>
          </Link>
        }
      />

      <div className="flex flex-col sm:flex-row gap-4 items-center shrink-0 bg-card/20 p-4 rounded-[2px] border border-border/40">
        <Form action="/metrics" className="flex-1 flex gap-3 w-full">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              name="q"
              placeholder="Search metrics by name or description..."
              defaultValue={q}
              className="pl-9 h-9 w-full bg-background border-border shadow-sm transition-all focus-visible:ring-1 rounded-[2px] text-xs font-mono"
            />
          </div>

          <div className="relative w-40">
            <select
              name="type"
              defaultValue={typeFilter}
              className="h-9 pl-3 pr-8 rounded-[2px] border border-border bg-background text-xs shadow-sm appearance-none focus:outline-none focus:ring-1 focus:ring-ring w-full font-mono"
            >
              <option value="all">All Types</option>
              <option value="ai-judge">AI Judge</option>
              <option value="primitive">Primitive</option>
            </select>
            <Filter className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          </div>

          <Button type="submit" variant="secondary" className="h-9 px-6 font-mono text-xs uppercase tracking-wider shadow-sm rounded-[2px]">
            Search
          </Button>
        </Form>
      </div>

      <MetricsTableClient metrics={metrics} />
    </div>
  );
}
