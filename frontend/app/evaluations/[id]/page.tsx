import {
  getEvaluation,
  getEvaluationPipelines,
  getEvaluationSummary,
  getPipeline,
} from "@/lib/api/evaluations";
import { fetchDataset } from "@/lib/api/datasets";
import { getRuntimes } from "@/lib/api/runtimes";
import { EvaluationDetailsClient } from "@/components/evaluations/evaluation-details-client";
import { PageHeader } from "@/components/ui/page-header";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function EvaluationDetailsPage(props: {
  params: Promise<{ id: string }>;
}) {
  const params = await props.params;
  const evaluationId = params.id;

  // Fetch summary first to ensure the evaluation job exists
  const summary = await getEvaluationSummary(evaluationId).catch(() => null);

  if (!summary) {
    return (
      <div className="p-8 max-w-6xl mx-auto space-y-8 bg-background">
        <Link href="/evaluations" className={cn(buttonVariants({ variant: "ghost" }), "-ml-4")}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Evaluations
        </Link>
        <div className="flex flex-col items-center justify-center h-64 border border-zinc-800 rounded-[2px] bg-card">
          <p className="text-muted-foreground font-mono text-xs">Evaluation job not found or failed to load.</p>
        </div>
      </div>
    );
  }

  // Fetch pipelines, full job details, runtimes, and pipeline config in parallel
  const [pipelines, job, runtimes, pipeline] = await Promise.all([
    getEvaluationPipelines(evaluationId).catch(() => []),
    getEvaluation(evaluationId).catch(() => null),
    getRuntimes().catch(() => []),
    getPipeline(summary.pipeline_id).catch(() => null),
  ]);

  // If we found the job, fetch the corresponding dataset
  let dataset = null;
  if (job && job.dataset_id) {
    dataset = await fetchDataset(job.dataset_id).catch(() => null);
  }

  return (
    <div className="p-8 w-full space-y-8 bg-background flex flex-col min-h-[calc(100vh-6.5rem)] h-auto pb-12 text-foreground">
      <div className="space-y-4 shrink-0">
        <Link href="/evaluations" className={cn(buttonVariants({ variant: "ghost" }), "-ml-4 text-xs font-mono")}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Evaluations
        </Link>

        <PageHeader
          preTitle="Diagnostics / Evaluation details"
          title={`Job: ${summary.job_id.split("-")[0]}`}
          description={
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-xs font-mono mt-2">
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <span>Pipeline:</span>
                <Link
                  href={`/pipelines/${summary.pipeline_id}`}
                  className="inline-flex items-center px-2 py-0.5 text-[11px] font-mono rounded-[2px] bg-secondary/50 text-primary border border-border/30 hover:bg-secondary hover:border-primary/30 transition-colors"
                >
                  {pipeline ? pipeline.name : summary.pipeline_id.split("-")[0]}
                </Link>
              </div>
              {dataset && (
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <span>Dataset:</span>
                  <Link
                    href={`/datasets/${dataset.id}`}
                    className="inline-flex items-center px-2 py-0.5 text-[11px] font-mono rounded-[2px] bg-secondary/50 text-primary border border-border/30 hover:bg-secondary hover:border-primary/30 transition-colors"
                  >
                    {dataset.name}
                  </Link>
                </div>
              )}
            </div>
          }
        />
      </div>

      <div className="flex flex-col flex-1 w-full min-h-0 min-w-0">
        <EvaluationDetailsClient
          summary={summary}
          pipelines={pipelines}
          dataset={dataset}
          runtimes={runtimes}
        />
      </div>
    </div>
  );
}
