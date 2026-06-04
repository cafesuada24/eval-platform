import { getEvaluations } from "@/lib/api/evaluations";
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
import { ChevronRight } from "lucide-react";
import Form from "next/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export const dynamic = "force-dynamic";

export default async function EvaluationsPage(props: {
  searchParams: Promise<{ q?: string }>;
}) {
  const searchParams = await props.searchParams;
  const q = searchParams.q || "";

  // Fetch from the new list endpoint
  let runs = await getEvaluations();

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

  return (
    <div className="container mx-auto py-8 max-w-5xl">
      <div className="flex flex-col gap-2 mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Dataset Run Results</h1>
        <p className="text-muted-foreground">
          View all recent evaluation batches and their overarching pass rates.
        </p>
      </div>

      <div className="flex items-center justify-between mb-6">
        <Form action="/evaluations" className="flex w-full max-w-sm gap-2">
          <Input
            name="q"
            defaultValue={q}
            placeholder="Search by ID or name..."
            className="flex-1"
          />
          <Button type="submit" variant="secondary">
            Search
          </Button>
        </Form>
      </div>

      <div className="border rounded-md bg-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead>Job ID</TableHead>
              <TableHead>Pipeline</TableHead>
              <TableHead>Dataset</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right w-32">Pass Rate</TableHead>
              <TableHead className="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground h-32">
                  No evaluation runs found.
                </TableCell>
              </TableRow>
            ) : (
              runs.map((run) => {
                const pipelineStr = run.pipeline_name || run.pipeline_id.split("-")[0];
                const datasetStr = run.dataset_name || run.dataset_id.split("-")[0];
                
                // Determine pass rate
                let passRate = run.pass_rate;
                if (passRate === undefined && run.pipeline_run_results) {
                  // Fallback calculation if possible
                  const total = run.pipeline_run_results.length;
                  const passes = run.pipeline_run_results.filter(
                    (r) => r.overall_status === 0 || r.overall_status === "PASS"
                  ).length;
                  passRate = total > 0 ? (passes / total) * 100 : 0;
                }

                return (
                  <TableRow key={run.job_id} className="group hover:bg-muted/50 transition-colors cursor-pointer">
                    <TableCell className="font-mono text-xs font-medium">
                      <Link href={`/evaluations/${run.job_id}`} className="absolute inset-0 z-10">
                        <span className="sr-only">View Details</span>
                      </Link>
                      {run.job_id.split("-")[0]}...
                    </TableCell>
                    <TableCell className="font-medium">{pipelineStr}</TableCell>
                    <TableCell className="text-muted-foreground">{datasetStr}</TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={
                          run.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20"
                            : run.status === "FAILED"
                            ? "bg-rose-500/10 text-rose-600 hover:bg-rose-500/20"
                            : "bg-blue-500/10 text-blue-600 hover:bg-blue-500/20"
                        }
                      >
                        {run.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {passRate !== undefined ? (
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-1.5 bg-secondary rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                passRate >= 80
                                  ? "bg-emerald-500"
                                  : passRate >= 50
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                              }`}
                              style={{ width: `${passRate}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium w-9 text-right">
                            {passRate.toFixed(0)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">N/A</span>
                      )}
                    </TableCell>
                    <TableCell>
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
