import {
  getEvaluationPipelines,
  getEvaluationSummary,
} from "@/lib/api/evaluations";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MetricSummaryCard } from "@/components/evaluations/metric-summary-card";
import { PipelineResultsTable } from "@/components/evaluations/pipeline-results-table";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function EvaluationDetailsPage(props: {
  params: Promise<{ id: string }>;
}) {
  const params = await props.params;
  const evaluationId = params.id;

  // We can fetch summary and pipelines in parallel
  const [summary, pipelines] = await Promise.all([
    getEvaluationSummary(evaluationId).catch(() => null),
    getEvaluationPipelines(evaluationId).catch(() => []),
  ]);

  if (!summary) {
    return (
      <div className="container mx-auto py-8 max-w-5xl">
        <Link href="/evaluations" className={cn(buttonVariants({ variant: "ghost" }), "mb-6 -ml-4")}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Evaluations
        </Link>
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-card">
          <p className="text-muted-foreground">Evaluation not found or failed to load.</p>
        </div>
      </div>
    );
  }

  // Calculate overall pass rate across all metrics for the header
  const totalRuns = summary.metrics.reduce((acc, m) => acc + m.total_runs, 0);
  const totalPasses = summary.metrics.reduce((acc, m) => acc + m.pass_count, 0);
  const overallPassRate = totalRuns > 0 ? (totalPasses / totalRuns) * 100 : 0;

  return (
    <div className="container mx-auto py-8 max-w-5xl">
        <Link href="/evaluations" className={cn(buttonVariants({ variant: "ghost" }), "mb-6 -ml-4")}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Evaluations
        </Link>

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Evaluation Details</h1>
          <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
            <span>Job: {summary.job_id.split("-")[0]}</span>
            <span>Pipeline: {summary.pipeline_id.split("-")[0]}</span>
          </div>
        </div>
        
        {/* Overall Pass Rate Badge */}
        <div className="flex flex-col items-end">
          <span className="text-sm text-muted-foreground mb-1">Overall Pass Rate</span>
          <div className="text-3xl font-bold">
            {overallPassRate.toFixed(1)}%
          </div>
        </div>
      </div>

      <Tabs defaultValue="metrics" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="metrics">Metrics Summary</TabsTrigger>
          <TabsTrigger value="testcases">Test Cases</TabsTrigger>
        </TabsList>
        
        <TabsContent value="metrics" className="focus-visible:outline-none">
          {summary.metrics.length === 0 ? (
            <div className="border rounded-md p-8 text-center text-muted-foreground bg-card">
              No metrics data available for this evaluation.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {summary.metrics.map((metric) => (
                <MetricSummaryCard
                  key={metric.metric_id}
                  title={`Metric: ${metric.metric_id.split("-")[0]}`}
                  summary={metric}
                />
              ))}
            </div>
          )}
        </TabsContent>
        
        <TabsContent value="testcases" className="focus-visible:outline-none">
          <PipelineResultsTable results={pipelines} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
