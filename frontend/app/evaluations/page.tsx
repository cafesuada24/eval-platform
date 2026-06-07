import { getEvaluations, getPipelines } from "@/lib/api/evaluations";
import { fetchDatasets } from "@/lib/api/datasets";
import { BatchRunResult } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { ChevronRight, ArrowUpDown } from "lucide-react";
import Form from "next/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

import { PageHeader } from "@/components/ui/page-header";

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

export default async function EvaluationsPage(props: {
  searchParams: Promise<{ q?: string; sort?: string; order?: string }>;
}) {
  const searchParams = await props.searchParams;
  const q = searchParams.q || "";
  const sort = searchParams.sort || "created_at"; // Default sort by run time
  const order = searchParams.order || "desc"; // Default descending order (newest first)

  // Fetch all runs, pipelines, and datasets in parallel
  const [allRuns, pipelines, datasets] = await Promise.all([
    getEvaluations(),
    getPipelines().catch(() => []),
    fetchDatasets().catch(() => []),
  ]);

  const pipelineMap = new Map(pipelines.map((p) => [p.id, p.name]));
  const datasetMap = new Map(datasets.map((d) => [d.id, d.name]));

  // Populate names on run results
  let runs = allRuns.map((run) => ({
    ...run,
    pipeline_name: pipelineMap.get(run.pipeline_id) || run.pipeline_name,
    dataset_name: datasetMap.get(run.dataset_id) || run.dataset_name,
  }));

  // Basic client-side filtering if search query exists
  if (q) {
    const lowerQ = q.toLowerCase();
    runs = runs.filter(
      (run) =>
        run.job_id.toLowerCase().includes(lowerQ) ||
        run.pipeline_id.toLowerCase().includes(lowerQ) ||
        run.dataset_id.toLowerCase().includes(lowerQ) ||
        run.pipeline_name?.toLowerCase().includes(lowerQ) ||
        run.dataset_name?.toLowerCase().includes(lowerQ)
    );
  }

  // Pass rate calculation helper
  const getPassRate = (run: BatchRunResult) => {
    if (run.pass_rate !== undefined) return run.pass_rate;
    if (!run.pipeline_run_results || run.pipeline_run_results.length === 0) return 0;
    const total = run.pipeline_run_results.length;
    const passes = run.pipeline_run_results.filter(
      (r: { overall_status: number | string }) => r.overall_status === 0 || r.overall_status === "PASS"
    ).length;
    return total > 0 ? (passes / total) * 100 : 0;
  };

  // Perform client-side sorting based on query params
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
    } else if (sort === "dataset_name") {
      valA = (a.dataset_name || a.dataset_id).toLowerCase();
      valB = (b.dataset_name || b.dataset_id).toLowerCase();
    } else if (sort === "status") {
      valA = a.status.toLowerCase();
      valB = b.status.toLowerCase();
    }

    if (valA < valB) return order === "asc" ? -1 : 1;
    if (valA > valB) return order === "asc" ? 1 : -1;
    return 0;
  });

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

      <div className="border border-border/40 rounded-[2px] overflow-hidden bg-card/30 backdrop-blur-xs shadow-sm">
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
                      <Link
                        href={`/pipelines/${run.pipeline_id}`}
                        className="z-20 relative inline-flex items-center px-2 py-0.5 text-[11px] font-mono rounded-[2px] bg-secondary/50 text-foreground border border-border/30 hover:bg-secondary hover:border-primary/30 transition-colors"
                      >
                        {pipelineStr}
                      </Link>
                    </TableCell>
                    <TableCell className="py-3.5">
                      <Link
                        href={`/datasets/${run.dataset_id}`}
                        className="z-20 relative inline-flex items-center px-2 py-0.5 text-[11px] font-mono rounded-[2px] bg-secondary/50 text-muted-foreground border border-border/30 hover:bg-secondary hover:text-foreground hover:border-primary/30 transition-colors"
                      >
                        {datasetStr}
                      </Link>
                    </TableCell>
                    <TableCell className="py-3.5">
                      <Badge
                        variant="secondary"
                        className={`rounded-[2px] font-mono text-[9px] font-semibold uppercase ${
                          run.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border border-emerald-500/20"
                            : run.status === "FAILED"
                            ? "bg-rose-500/10 text-rose-600 hover:bg-rose-500/20 border border-rose-500/20"
                            : "bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 border border-blue-500/20"
                        }`}
                      >
                        {run.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground py-3.5">{timeStr}</TableCell>
                    <TableCell className="text-right py-3.5">
                      {passRate !== undefined ? (
                        <div className="flex items-center justify-end gap-2.5">
                          <div className="w-16 h-1.5 bg-secondary rounded-[1px] overflow-hidden border border-border/20">
                            <div
                              className={`h-full rounded-[1px] ${
                                passRate >= 80
                                  ? "bg-emerald-500"
                                  : passRate >= 50
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                              }`}
                              style={{ width: `${passRate}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono font-medium w-8 text-right text-foreground/80">
                            {passRate.toFixed(0)}%
                          </span>
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
      </div>
    </div>
  );
}
