import { calculateMetricRatios, filterRunsByMetric } from "./lib/diagnostic-utils";
import { AssertionStatus } from "./lib/api/evaluations";

const mockMetrics = [
  {
    metric_id: "m1",
    metric_name: "helpful",
    average_score: 4,
    pass_count: 8,
    warning_count: 1,
    fail_count: 1,
    pass_rate: 80,
    total_runs: 10
  }
];

const mockRuns = [
  {
    run_id: "r1",
    overall_status: AssertionStatus.PASS,
    metric_results: [
      { metric_id: "m1", metric_name: "helpful", score: 4.5, assertion_status: AssertionStatus.PASS, run_id: "r1", justification: "Good" }
    ],
    testcase_id: "tc1",
    pipeline_id: "p1",
    evaluation_context_id: "c1"
  },
  {
    run_id: "r2",
    overall_status: AssertionStatus.FAIL,
    metric_results: [
      { metric_id: "m1", metric_name: "helpful", score: 1.0, assertion_status: AssertionStatus.FAIL, run_id: "r2", justification: "Bad" }
    ],
    testcase_id: "tc2",
    pipeline_id: "p1",
    evaluation_context_id: "c1"
  }
];

// Test calculations
const ratios = calculateMetricRatios(mockMetrics[0]);
if (ratios.passWidth !== 80 || ratios.warnWidth !== 10 || ratios.failWidth !== 10) {
  throw new Error(`Calculation failed: ${JSON.stringify(ratios)}`);
}

// Test zero/empty metric edge case
const zeroMetric = {
  metric_id: "m2",
  metric_name: "empty",
  average_score: 0,
  pass_count: 0,
  warning_count: 0,
  fail_count: 0,
  pass_rate: 0,
  total_runs: 0
};
const zeroRatios = calculateMetricRatios(zeroMetric);
if (zeroRatios.passWidth !== 0 || zeroRatios.warnWidth !== 0 || zeroRatios.failWidth !== 0) {
  throw new Error(`Zero calculation failed: ${JSON.stringify(zeroRatios)}`);
}

// Test filtering
const filtered = filterRunsByMetric(mockRuns, { metricId: "m1", status: AssertionStatus.FAIL });
if (filtered.length !== 1 || filtered[0].run_id !== "r2") {
  throw new Error(`Filtering failed: ${JSON.stringify(filtered)}`);
}

// Test filtering with missing metric
const filteredMissing = filterRunsByMetric(mockRuns, { metricId: "nonexistent", status: AssertionStatus.FAIL });
if (filteredMissing.length !== 0) {
  throw new Error(`Filtering for nonexistent metric failed: ${JSON.stringify(filteredMissing)}`);
}

console.log("✅ All tests passed successfully!");
