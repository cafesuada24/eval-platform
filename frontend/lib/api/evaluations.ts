import { BatchRunResult } from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export enum AssertionStatus {
  PASS = 0,
  WARNING = 1,
  FAIL = 2,
}

export interface MetricSummary {
  metric_id: string; // UUID
  average_score: number;
  pass_count: number;
  fail_count: number;
  warning_count: number;
  pass_rate: number; // percentage (0.0 - 100.0)
  total_runs: number;
}

export interface BatchSummary {
  job_id: string; // UUID
  pipeline_id: string; // UUID
  metrics: MetricSummary[];
}

export interface MetricRunResult {
  metric_id: string; // UUID
  score: number;
  justification: string;
  assertion_status: AssertionStatus;
  run_id: string; // UUID
}

export interface PipelineRunResult {
  evaluation_context_id: string; // UUID
  pipeline_id: string; // UUID
  overall_status: AssertionStatus;
  metric_results: MetricRunResult[];
  testcase_id: string | null; // UUID - identifies the testcase this run belongs to
  run_id: string; // UUID - unique ID for this pipeline run
}

export async function getEvaluations(): Promise<BatchRunResult[]> {
  const res = await fetch(`${API_BASE_URL}/evaluations`, {
    cache: "no-store", // Since evaluations can be running, we avoid aggressive caching
  });
  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error(`Failed to fetch evaluations: ${res.statusText}`);
  }
  return res.json();
}

export async function getEvaluationSummary(evaluationId: string): Promise<BatchSummary> {
  const res = await fetch(`${API_BASE_URL}/evaluations/${evaluationId}/summary`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch evaluation summary: ${res.statusText}`);
  }
  return res.json();
}

export async function getEvaluationPipelines(evaluationId: string): Promise<PipelineRunResult[]> {
  const res = await fetch(`${API_BASE_URL}/evaluations/${evaluationId}/pipelines`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch evaluation pipelines: ${res.statusText}`);
  }
  return res.json();
}

export async function getEvaluationMetrics(evaluationId: string, metricId: string): Promise<MetricRunResult[]> {
  const res = await fetch(`${API_BASE_URL}/evaluations/${evaluationId}/metrics/${metricId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch evaluation metric results: ${res.statusText}`);
  }
  return res.json();
}
