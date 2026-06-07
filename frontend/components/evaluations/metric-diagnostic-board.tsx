"use client";

import { MetricSummary, AssertionStatus } from "@/lib/api/evaluations";
import { calculateMetricRatios } from "@/lib/diagnostic-utils";
import { cn } from "@/lib/utils";
import { BarChart3, XCircle } from "lucide-react";

export interface MetricDiagnosticBoardProps {
  metrics: MetricSummary[];
  activeFilter: { metricId: string; status: AssertionStatus | null } | null;
  onFilterChange: (filter: { metricId: string; status: AssertionStatus | null } | null) => void;
}

export function MetricDiagnosticBoard({
  metrics,
  activeFilter,
  onFilterChange,
}: MetricDiagnosticBoardProps) {
  if (!metrics || metrics.length === 0) return null;

  const handleSegmentClick = (metricId: string, status: AssertionStatus) => {
    if (activeFilter?.metricId === metricId && activeFilter?.status === status) {
      onFilterChange(null);
    } else {
      onFilterChange({ metricId, status });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, metricId: string, status: AssertionStatus) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleSegmentClick(metricId, status);
    }
  };

  return (
    <div className="bg-card/30 border border-border/40 p-4 rounded-[2px] mb-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-primary" />
          <h3 className="text-xs font-semibold uppercase tracking-wider font-mono">Metrics Diagnostic Board</h3>
        </div>
        
        {activeFilter && (
          <button
            onClick={() => onFilterChange(null)}
            className="flex items-center gap-1.5 px-2 py-0.5 text-[9px] font-mono uppercase bg-rose-500/10 text-rose-500 border border-rose-500/20 rounded-[2px] cursor-pointer hover:bg-rose-500/20 transition-colors"
          >
            Clear Filter
            <XCircle className="h-3 w-3" />
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {metrics.map((metric) => {
          const { passWidth, warnWidth, failWidth } = calculateMetricRatios(metric);
          
          return (
            <div key={metric.metric_id} className="p-3 border border-border/40 bg-card/20 rounded-[2px] space-y-2">
              <div className="flex justify-between items-baseline text-xs font-mono">
                <span className="font-semibold text-foreground/90 truncate max-w-[180px]">{metric.metric_name}</span>
                <span className="text-muted-foreground text-[10px]">
                  Avg: {metric.average_score.toFixed(1)} • Rate: {metric.pass_rate.toFixed(0)}%
                </span>
              </div>
              
              <div className="flex h-4 bg-muted/40 rounded-[2px] overflow-hidden border border-border/10">
                {passWidth > 0 && (
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => handleSegmentClick(metric.metric_id, AssertionStatus.PASS)}
                    onKeyDown={(e) => handleKeyDown(e, metric.metric_id, AssertionStatus.PASS)}
                    title={`${metric.pass_count} passed`}
                    aria-label={`${metric.pass_count} passed runs`}
                    aria-pressed={activeFilter?.metricId === metric.metric_id && activeFilter?.status === AssertionStatus.PASS}
                    style={{ width: `${passWidth}%` }}
                    className={cn(
                      "bg-emerald-500 transition-all cursor-pointer hover:opacity-80 focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring",
                      activeFilter?.metricId === metric.metric_id && activeFilter?.status === AssertionStatus.PASS && "ring-2 ring-primary ring-inset"
                    )}
                  />
                )}
                {warnWidth > 0 && (
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => handleSegmentClick(metric.metric_id, AssertionStatus.WARNING)}
                    onKeyDown={(e) => handleKeyDown(e, metric.metric_id, AssertionStatus.WARNING)}
                    title={`${metric.warning_count} warnings`}
                    aria-label={`${metric.warning_count} warning runs`}
                    aria-pressed={activeFilter?.metricId === metric.metric_id && activeFilter?.status === AssertionStatus.WARNING}
                    style={{ width: `${warnWidth}%` }}
                    className={cn(
                      "bg-amber-500 transition-all cursor-pointer hover:opacity-80 focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring",
                      activeFilter?.metricId === metric.metric_id && activeFilter?.status === AssertionStatus.WARNING && "ring-2 ring-primary ring-inset"
                    )}
                  />
                )}
                {failWidth > 0 && (
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => handleSegmentClick(metric.metric_id, AssertionStatus.FAIL)}
                    onKeyDown={(e) => handleKeyDown(e, metric.metric_id, AssertionStatus.FAIL)}
                    title={`${metric.fail_count} failed`}
                    aria-label={`${metric.fail_count} failed runs`}
                    aria-pressed={activeFilter?.metricId === metric.metric_id && activeFilter?.status === AssertionStatus.FAIL}
                    style={{ width: `${failWidth}%` }}
                    className={cn(
                      "bg-rose-500 transition-all cursor-pointer hover:opacity-80 focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring",
                      activeFilter?.metricId === metric.metric_id && activeFilter?.status === AssertionStatus.FAIL && "ring-2 ring-primary ring-inset"
                    )}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

