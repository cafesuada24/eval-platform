/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState, useMemo, useCallback } from "react";
import {
  PipelineRunResult,
  BatchSummary,
  AssertionStatus,
  MetricRunResult,
} from "@/lib/api/evaluations";
import { TestCase, RuntimeState } from "@/lib/types";
import {
  Search,
  Copy,
  Check,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Code,
  Terminal,
  Activity,
  ChevronRight,
  Clock,
  Coins,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { MetricDiagnosticBoard } from "./metric-diagnostic-board";
import { filterRunsByMetric } from "@/lib/diagnostic-utils";

interface EvaluationDetailsClientProps {
  summary: BatchSummary;
  pipelines: PipelineRunResult[];
  dataset: any | null;
  runtimes: RuntimeState[];
}

export function EvaluationDetailsClient({
  summary,
  pipelines,
  dataset,
  runtimes,
}: EvaluationDetailsClientProps) {
  const [selectedRunId, setSelectedRunId] = useState<string>(
    pipelines.length > 0 ? pipelines[0].run_id : ""
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [metricFilter, setMetricFilter] = useState<{
    metricId: string;
    status: AssertionStatus | null;
  } | null>(null);
  const [copiedText, setCopiedText] = useState(false);
  const [isRawJsonExpanded, setIsRawJsonExpanded] = useState(true);

  // Map dataset cases for quick lookup
  const caseMap = useMemo(() => {
    const map = new Map<string, TestCase>();
    const datasetCases = dataset?.cases;
    if (Array.isArray(datasetCases)) {
      datasetCases.forEach((tc: any) => {
        if (tc.id) map.set(tc.id, tc);
      });
    }
    return map;
  }, [dataset]);

  // Client-side matching of PipelineRunResult to RuntimeState
  // We match based on test case query or prompt text matches
  const matchRuntimeState = useCallback((run: PipelineRunResult, testcase: TestCase | undefined) => {
    if (!testcase) return undefined;

    const tcQuery =
      testcase.inputs.query ||
      testcase.inputs.text ||
      testcase.inputs.user_prompt ||
      testcase.inputs.prompt ||
      Object.values(testcase.inputs)[0];

    if (!tcQuery) return undefined;

    return runtimes.find((rt) => {
      // 1. Check generation event query/input
      const genEvent = rt.events.find((e) => e.event_type === "generation");
      if (genEvent && genEvent.payload) {
        const genInput = genEvent.payload.input_text || genEvent.payload.query;
        if (genInput && String(genInput).trim() === String(tcQuery).trim()) {
          return true;
        }
      }
      // 2. Check retrieval event query
      const retEvent = rt.events.find((e) => e.event_type === "retrieval");
      if (retEvent && retEvent.payload) {
        const retQuery = retEvent.payload.query;
        if (retQuery && String(retQuery).trim() === String(tcQuery).trim()) {
          return true;
        }
      }
      return false;
    });
  }, [runtimes]);

  // Process pipelines to inject dataset testcase and matched runtime
  const runsWithDetails = useMemo(() => {
    return pipelines.map((run) => {
      const testcase = run.testcase_id ? caseMap.get(run.testcase_id) : undefined;
      const matchedRuntime = matchRuntimeState(run, testcase);
      return {
        ...run,
        testcase,
        runtime: matchedRuntime,
      };
    });
  }, [pipelines, caseMap, matchRuntimeState]);

  // Filter runs based on search query, status filter badge, and metric filter
  const filteredRuns = useMemo(() => {
    const step1 = runsWithDetails.filter((run) => {
      // 1. Status Filter
      if (statusFilter !== "ALL") {
        if (statusFilter === "PASS" && run.overall_status !== AssertionStatus.PASS) return false;
        if (statusFilter === "WARNING" && run.overall_status !== AssertionStatus.WARNING) return false;
        if (statusFilter === "FAIL" && run.overall_status !== AssertionStatus.FAIL) return false;
      }

      // 2. Search Query (matches Run ID, Testcase ID, or inputs)
      if (searchQuery.trim() !== "") {
        const query = searchQuery.toLowerCase();
        const runIdMatch = run.run_id.toLowerCase().includes(query);
        const tcIdMatch = run.testcase_id ? run.testcase_id.toLowerCase().includes(query) : false;
        
        // Match against testcase inputs values
        let inputMatch = false;
        if (run.testcase && run.testcase.inputs) {
          inputMatch = Object.values(run.testcase.inputs).some((val) =>
            String(val).toLowerCase().includes(query)
          );
        }
        
        return runIdMatch || tcIdMatch || inputMatch;
      }

      return true;
    });

    return filterRunsByMetric(step1, metricFilter);
  }, [runsWithDetails, statusFilter, searchQuery, metricFilter]);

  // Find currently selected run details
  const selectedRun = useMemo(() => {
    return runsWithDetails.find((r) => r.run_id === selectedRunId);
  }, [runsWithDetails, selectedRunId]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  const getStatusBadge = (status: AssertionStatus) => {
    switch (status) {
      case AssertionStatus.PASS:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 text-emerald-700 dark:text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 rounded-[2px]">
            <CheckCircle2 className="h-3 w-3" /> PASS
          </span>
        );
      case AssertionStatus.WARNING:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20 rounded-[2px]">
            <AlertTriangle className="h-3 w-3" /> WARN
          </span>
        );
      case AssertionStatus.FAIL:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20 rounded-[2px]">
            <XCircle className="h-3 w-3" /> FAIL
          </span>
        );
    }
  };

  const getStatusDot = (status: AssertionStatus) => {
    switch (status) {
      case AssertionStatus.PASS:
        return <span className="h-2 w-2 bg-emerald-500 rounded-full shrink-0" />;
      case AssertionStatus.WARNING:
        return <span className="h-2 w-2 bg-amber-500 rounded-full shrink-0 animate-pulse" />;
      case AssertionStatus.FAIL:
        return <span className="h-2 w-2 bg-rose-500 rounded-full shrink-0" />;
    }
  };

  // Get first preview text for run item
  const getRunPreview = (run: any) => {
    if (run.testcase && run.testcase.inputs) {
      const firstVal =
        run.testcase.inputs.query ||
        run.testcase.inputs.text ||
        run.testcase.inputs.user_prompt ||
        Object.values(run.testcase.inputs)[0];
      return String(firstVal);
    }
    return "No input context available";
  };

  return (
    <div className="flex flex-col h-full w-full min-h-0 min-w-0">

      {/* Render Metric Diagnostic Board */}
      <MetricDiagnosticBoard
        metrics={summary.metrics}
        activeFilter={metricFilter}
        onFilterChange={setMetricFilter}
      />

      {/* Main Split Pane Layout */}
      <div className="h-[750px] w-full min-w-0 border border-border bg-card/10 rounded-[2px] overflow-hidden flex flex-row shrink-0">
          
          {/* Left Master Pane: Run List */}
          <div className="w-[30%] min-w-[280px] max-w-[400px] flex flex-col bg-card shrink-0 border-r border-border">
            {/* Search and Filters */}
            <div className="p-4 border-b border-border space-y-3 bg-muted/10">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Filter by Run ID, input text..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-9 bg-background border-border text-xs font-mono rounded-[2px] focus-visible:ring-ring"
                />
              </div>
              
              {/* Filter Badges */}
              <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-none">
                {[
                  { label: "All", value: "ALL", count: pipelines.length },
                  {
                    label: "Passed",
                    value: "PASS",
                    count: pipelines.filter((p) => p.overall_status === AssertionStatus.PASS).length,
                    activeClass: "border-emerald-500/30 text-emerald-700 dark:text-emerald-600 dark:text-emerald-400 bg-emerald-500/10",
                  },
                  {
                    label: "Warning",
                    value: "WARNING",
                    count: pipelines.filter((p) => p.overall_status === AssertionStatus.WARNING).length,
                    activeClass: "border-amber-500/30 text-amber-700 dark:text-amber-400 bg-amber-500/10",
                  },
                  {
                    label: "Failed",
                    value: "FAIL",
                    count: pipelines.filter((p) => p.overall_status === AssertionStatus.FAIL).length,
                    activeClass: "border-rose-500/30 text-rose-700 dark:text-rose-400 bg-rose-500/10",
                  },
                ].map((f) => {
                  const isActive = statusFilter === f.value;
                  return (
                    <button
                      key={f.value}
                      onClick={() => setStatusFilter(f.value)}
                      className={cn(
                        "px-2.5 py-1 text-[10px] font-mono border rounded-[2px] transition-all flex items-center gap-1.5 shrink-0 cursor-pointer",
                        isActive
                          ? f.activeClass || "border-border text-foreground bg-accent"
                          : "border-border/60 text-muted-foreground hover:text-foreground hover:border-border bg-transparent"
                      )}
                    >
                      {f.label}
                      <span className="px-1 text-[9px] bg-background border border-border rounded-[2px] text-muted-foreground">
                        {f.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Run List Container */}
            <div className="flex-1 overflow-y-auto divide-y divide-border/30 bg-transparent">
              {filteredRuns.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-muted-foreground text-xs p-4">
                  <Activity className="h-6 w-6 text-muted-foreground/40 mb-2" />
                  No evaluation runs match selection.
                </div>
              ) : (
                filteredRuns.map((run) => {
                  const isSelected = run.run_id === selectedRunId;
                  return (
                    <div
                      key={run.run_id}
                      onClick={() => setSelectedRunId(run.run_id)}
                      className={cn(
                        "p-4 cursor-pointer transition-all flex flex-col gap-2 relative hover:bg-accent/50",
                        isSelected
                          ? "bg-accent border-l-[3px] border-primary"
                          : "border-l-[3px] border-transparent"
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          {getStatusDot(run.overall_status)}
                          <span className="font-mono text-[10px] font-semibold text-foreground">
                            run_{run.run_id.split("-")[0]}
                          </span>
                        </div>
                        <span className="text-[9px] text-muted-foreground font-mono">
                          tc_{run.testcase_id?.split("-")[0] || "n/a"}
                        </span>
                      </div>
                      
                      {/* Run Input Preview Excerpt */}
                      <p className="text-[11px] text-muted-foreground font-mono truncate whitespace-nowrap pl-4">
                        {getRunPreview(run)}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Detail Pane: Trace Inspector */}
          <div className="flex-1 min-w-0 flex flex-col bg-card">
            {selectedRun ? (
              <div className="flex flex-col h-full min-h-0 min-w-0">
                
                {/* Selected Run Header */}
                <div className="p-6 border-b border-border flex items-start justify-between gap-4 bg-muted/10">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-3">
                      <h2 className="text-base font-bold tracking-tight font-mono">
                        Pipeline Run Result
                      </h2>
                      {getStatusBadge(selectedRun.overall_status)}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground font-mono">
                      <span className="flex items-center gap-1">
                        <Terminal className="h-3 w-3" /> Run ID: <span className="text-foreground select-all">{selectedRun.run_id}</span>
                      </span>
                      {selectedRun.testcase_id && (
                        <span>
                          Test Case ID: <span className="text-foreground select-all">{selectedRun.testcase_id}</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Tabbed Inspector Content */}
                <Tabs defaultValue="trace" className="flex-1 flex flex-col min-h-0 min-w-0">
                  <div className="px-6 border-b border-border bg-muted/5">
                    <TabsList className="h-10 p-0 bg-transparent gap-6 rounded-none border-none">
                      <TabsTrigger
                        value="trace"
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-foreground bg-transparent hover:text-foreground text-xs font-semibold tracking-wider uppercase"
                      >
                        Trace Context
                      </TabsTrigger>
                      <TabsTrigger
                        value="metrics"
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-foreground bg-transparent hover:text-foreground text-xs font-semibold tracking-wider uppercase"
                      >
                        Metric Assertions ({selectedRun.metric_results.length})
                      </TabsTrigger>
                    </TabsList>
                  </div>

                  <div className="flex-1 overflow-y-auto p-6 min-h-0 min-w-0">
                    {/* Tab 1: Trace Context */}
                    <TabsContent value="trace" className="space-y-6 focus-visible:outline-none mt-0 w-full min-w-0">
                      {/* Metadata / Latency Header */}
                      {selectedRun.runtime && (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 border border-border p-4 bg-muted/20 rounded-[2px] font-mono text-xs">
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
                            <div>
                              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Latency</div>
                              <div className="font-semibold text-foreground">
                                {selectedRun.runtime.usage?.latency_ms
                                  ? `${(selectedRun.runtime.usage.latency_ms / 1000).toFixed(2)}s`
                                  : "N/A"}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            <Coins className="h-4 w-4 text-muted-foreground shrink-0" />
                            <div>
                              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Tokens</div>
                              <div className="font-semibold text-foreground">
                                {selectedRun.runtime.usage?.input_tokens !== undefined &&
                                selectedRun.runtime.usage?.output_tokens !== undefined ? (
                                  `${selectedRun.runtime.usage.input_tokens} in / ${selectedRun.runtime.usage.output_tokens} out`
                                ) : (
                                  "N/A"
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 col-span-2 md:col-span-1">
                            <Activity className="h-4 w-4 text-muted-foreground shrink-0" />
                            <div>
                              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Events Captured</div>
                              <div className="font-semibold text-foreground">
                                {selectedRun.runtime.events?.length || 0} Telemetry Nodes
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Testcase Inputs */}
                      <div className="space-y-3">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground text-mono font-mono">
                          Test Case Inputs
                        </h3>
                        {selectedRun.testcase ? (
                          <div className="border border-border rounded-[2px] divide-y divide-border bg-muted/5">
                            {Object.entries(selectedRun.testcase.inputs).map(([key, value]) => (
                              <div key={key} className="p-4 grid grid-cols-1 md:grid-cols-4 gap-2 text-xs">
                                <span className="font-mono font-semibold text-muted-foreground md:col-span-1">{key}</span>
                                <span className="font-mono text-foreground md:col-span-3 whitespace-pre-wrap select-text break-words">
                                  {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="p-4 border border-zinc-800 rounded-[2px] bg-muted/10 text-xs text-muted-foreground font-mono">
                            No dataset input definitions linked. Testcase ID: {selectedRun.testcase_id}
                          </div>
                        )}
                      </div>

                      {/* Testcase Expected Outputs */}
                      <div className="space-y-3">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground text-mono font-mono">
                          Expected Outputs
                        </h3>
                        {selectedRun.testcase ? (
                          <div className="border border-border rounded-[2px] divide-y divide-border bg-muted/5">
                            {Object.entries(selectedRun.testcase.expected_outputs).map(([key, value]) => (
                              <div key={key} className="p-4 grid grid-cols-1 md:grid-cols-4 gap-2 text-xs">
                                <span className="font-mono font-semibold text-muted-foreground md:col-span-1">{key}</span>
                                <span className="font-mono text-foreground md:col-span-3 whitespace-pre-wrap select-text break-words">
                                  {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="p-4 border border-zinc-800 rounded-[2px] bg-muted/10 text-xs text-muted-foreground font-mono">
                            No expected output defined.
                          </div>
                        )}
                      </div>

                      {/* Intermediate Telemetry / Generation Output if runtime matches */}
                      {selectedRun.runtime && (
                        <div className="space-y-3">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground text-mono font-mono">
                            Generation Trace Result
                          </h3>
                          <div className="border border-border rounded-[2px] divide-y divide-border bg-muted/5">
                            {selectedRun.runtime.events
                              .filter((e) => e.event_type === "generation")
                              .map((ev, idx) => (
                                <div key={ev.timestamp + idx} className="p-4 space-y-3 text-xs font-mono">
                                  <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                                    <span>Model: {ev.payload?.model || "Unknown"} ({ev.payload?.provider || ""})</span>
                                    <span>Latency: {ev.payload?.latency_ms ? `${(ev.payload.latency_ms / 1000).toFixed(2)}s` : "N/A"}</span>
                                  </div>
                                  <div className="grid grid-cols-1 md:grid-cols-4 gap-2 border-t border-border pt-3">
                                    <span className="font-semibold text-muted-foreground md:col-span-1">Generated Output</span>
                                    <span className="text-emerald-600 dark:text-emerald-600 dark:text-emerald-400 md:col-span-3 whitespace-pre-wrap select-text break-words">
                                      {ev.payload?.output_text || "No output text returned"}
                                    </span>
                                  </div>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}

                      {/* Raw JSON Code Block */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground text-mono font-mono">
                            Raw Trace Payload
                          </h3>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                const payload = {
                                  pipeline_run_result: selectedRun,
                                  testcase: selectedRun.testcase,
                                  runtime_trace: selectedRun.runtime,
                                };
                                copyToClipboard(JSON.stringify(payload, null, 2));
                              }}
                              className="h-7 px-2 text-[10px] font-mono rounded-[2px] cursor-pointer"
                            >
                              {copiedText ? (
                                <>
                                  <Check className="h-3 w-3 mr-1 text-emerald-600 dark:text-emerald-400" /> Copied
                                </>
                              ) : (
                                <>
                                  <Copy className="h-3 w-3 mr-1" /> Copy JSON
                                </>
                              )}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setIsRawJsonExpanded(!isRawJsonExpanded)}
                              className="h-7 px-2 text-[10px] font-mono rounded-[2px] cursor-pointer"
                            >
                              <Code className="h-3 w-3 mr-1" /> {isRawJsonExpanded ? "Collapse" : "Expand"}
                            </Button>
                          </div>
                        </div>
                        
                        {isRawJsonExpanded && (
                          <div className="border border-border rounded-[2px] bg-muted/10 p-4 overflow-x-auto max-h-96">
                            <pre className="text-[10px] font-mono text-muted-foreground select-text leading-relaxed">
                              {JSON.stringify(
                                {
                                  pipeline_run_result: selectedRun,
                                  testcase: selectedRun.testcase,
                                  runtime_trace: selectedRun.runtime,
                                },
                                null,
                                2
                              )}
                            </pre>
                          </div>
                        )}
                      </div>
                    </TabsContent>

                    {/* Tab 2: Metric Assertions */}
                    <TabsContent value="metrics" className="space-y-4 focus-visible:outline-none mt-0 w-full min-w-0">
                      {selectedRun.metric_results.length === 0 ? (
                        <div className="text-center text-muted-foreground p-8 font-mono text-xs">
                          No metric evaluation runs executed for this pipeline step.
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {selectedRun.metric_results.map((metric: MetricRunResult) => (
                            <div
                              key={metric.metric_id}
                              className="border border-border bg-muted/5 p-5 rounded-[2px] flex flex-col gap-4"
                            >
                              {/* Title block */}
                              <div className="flex items-start justify-between gap-4">
                                <div className="space-y-1">
                                  <h4 className="text-sm font-bold font-mono tracking-tight text-foreground">
                                    {metric.metric_name}
                                  </h4>
                                  <span className="text-[9px] text-muted-foreground font-mono block">
                                    Metric ID: {metric.metric_id}
                                  </span>
                                </div>
                                <div className="flex items-center gap-3">
                                  <div className="text-right">
                                    <div className="text-[10px] text-muted-foreground uppercase font-mono tracking-wider">Score</div>
                                    <div className="font-bold font-mono text-sm">{metric.score.toFixed(2)}</div>
                                  </div>
                                  {getStatusBadge(metric.assertion_status)}
                                </div>
                              </div>

                              <div className="h-px bg-border/60" />

                              {/* Justification & Evidence */}
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs font-mono">
                                
                                {/* Justification */}
                                <div className="md:col-span-2 space-y-2">
                                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">
                                    Evaluator Justification
                                  </span>
                                  <p className="text-foreground leading-relaxed whitespace-pre-wrap select-text">
                                    {metric.justification || "No justification returned by evaluator."}
                                  </p>
                                </div>

                                {/* Evidence & Improvements */}
                                <div className="space-y-4">
                                  {metric.evidence && (
                                    <div className="space-y-1.5">
                                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">
                                        Grounding Evidence
                                      </span>
                                      <div className="bg-background p-3 border border-border rounded-[2px] text-[10px] text-muted-foreground select-text whitespace-pre-wrap max-h-40 overflow-y-auto">
                                        {metric.evidence}
                                      </div>
                                    </div>
                                  )}
                                  
                                  {metric.improvements && (
                                    <div className="space-y-1.5">
                                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold text-amber-600 dark:text-amber-500/80">
                                        Suggested Improvements
                                      </span>
                                      <p className="text-amber-600 dark:text-amber-500/80 leading-relaxed whitespace-pre-wrap select-text">
                                        {metric.improvements}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </TabsContent>
                  </div>
                </Tabs>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-xs p-4">
                <ChevronRight className="h-6 w-6 text-muted-foreground/40 mb-2 rotate-90" />
                Select a run from the left list to inspect detailed telemetry traces.
              </div>
            )}
          </div>
      </div>
    </div>
  );
}
