# Evaluation Inspection API Endpoints

This document outlines the evaluation endpoints available for the frontend agent to implement. All routes are prefixed with `/api/v1/evaluations`.

## Overview
These endpoints allow the frontend to inspect the results of an evaluation batch job. They provide aggregated summaries, per-pipeline (test case) results, and per-metric results.

---

## 1. List All Evaluations
Fetches a list of all batch evaluation jobs.

**Endpoint:** `GET /`

**Response:** `BatchRunResult[]`

*(See `BatchRunResult` schema below)*

---

## 2. Batch Summary
Retrieves an aggregated summary of all metrics across all test cases in the given batch evaluation job.

**Endpoint:** `GET /{evaluation_id}/summary`

**Response (`BatchSummary`):**
```typescript
interface BatchSummary {
  job_id: string; // UUID
  pipeline_id: string; // UUID
  metrics: MetricSummary[];
}

interface MetricSummary {
  metric_id: string; // UUID
  average_score: number;
  pass_count: number;
  fail_count: number;
  warning_count: number;
  pass_rate: number; // percentage (0.0 - 100.0)
  total_runs: number;
}
```

---

---

## 3. Per-Testcase Result
Fetches the pipeline run result for a specific test case within the evaluation batch.

**Endpoint:** `GET /{evaluation_id}/testcases/{testcase_id}`

**Response (`PipelineRunResult`):**
*(See the `PipelineRunResult` schema below)*

---

## 3. All Pipeline Results (Raw List)
Fetches all pipeline run results for the entire batch job.

**Endpoint:** `GET /{evaluation_id}/pipelines`

**Response:** `PipelineRunResult[]`

---

## 4. Specific Pipeline Result
Fetches a specific pipeline run result using its unique run ID (rather than the test case ID).

**Endpoint:** `GET /{evaluation_id}/pipelines/{pipeline_run_id}`

**Response (`PipelineRunResult`):**
*(See the `PipelineRunResult` schema below)*

---

## 5. Per-Metric Results
Fetches all individual metric run results for a specific metric across the entire batch job.

**Endpoint:** `GET /{evaluation_id}/metrics/{metric_id}`

**Response:** `MetricRunResult[]`

---

## Core Models / Enums

### `AssertionStatus` (Enum)
```typescript
enum AssertionStatus {
  PASS = 0,
  WARNING = 1,
  FAIL = 2,
}
```

### `PipelineRunResult`
```typescript
interface PipelineRunResult {
  evaluation_context_id: string; // UUID
  pipeline_id: string; // UUID
  overall_status: AssertionStatus;
  metric_results: MetricRunResult[];
  testcase_id: string | null; // UUID - identifies the testcase this run belongs to
  run_id: string; // UUID - unique ID for this pipeline run
}
```

### `MetricRunResult`
```typescript
interface MetricRunResult {
  metric_id: string; // UUID
  score: number;
  justification: string;
  assertion_status: AssertionStatus;
  run_id: string; // UUID
}
```
