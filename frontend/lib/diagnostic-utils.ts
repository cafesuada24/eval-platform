import { MetricSummary, PipelineRunResult, AssertionStatus } from "./api/evaluations";

export interface MetricRatios {
  passWidth: number;
  warnWidth: number;
  failWidth: number;
}

export function calculateMetricRatios(metric: MetricSummary): MetricRatios {
  const sum = metric.pass_count + metric.warning_count + metric.fail_count;
  if (sum === 0 || metric.total_runs === 0) {
    return {
      passWidth: 0,
      warnWidth: 0,
      failWidth: 0,
    };
  }
  return {
    passWidth: (metric.pass_count / sum) * 100,
    warnWidth: (metric.warning_count / sum) * 100,
    failWidth: (metric.fail_count / sum) * 100,
  };
}

export function filterRunsByMetric(
  runs: PipelineRunResult[],
  filter: { metricId: string; status: AssertionStatus | null } | null
): PipelineRunResult[] {
  if (!filter) return runs;
  return runs.filter((run) => {
    const result = run.metric_results.find((m) => m.metric_id === filter.metricId);
    if (!result) return false;
    if (filter.status !== null && result.assertion_status !== filter.status) return false;
    return true;
  });
}
