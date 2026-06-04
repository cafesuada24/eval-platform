import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricSummary } from "@/lib/api/evaluations";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricSummaryCardProps {
  title: string;
  summary: MetricSummary;
}

export function MetricSummaryCard({ title, summary }: MetricSummaryCardProps) {
  // Color the progress bar based on pass_rate
  let progressColor = "bg-emerald-500";
  if (summary.pass_rate < 80) progressColor = "bg-amber-500";
  if (summary.pass_rate < 50) progressColor = "bg-rose-500";

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground truncate">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-between">
        <div className="mb-4">
          <div className="text-3xl font-bold">{summary.pass_rate.toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground mt-1">Pass Rate</p>
        </div>

        {/* Progress Bar */}
        <div className="h-2 w-full bg-secondary rounded-full overflow-hidden mb-4">
          <div
            className={cn("h-full rounded-full transition-all duration-500", progressColor)}
            style={{ width: `${summary.pass_rate}%` }}
          />
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-2 border-t pt-4 mt-auto">
          <div className="flex flex-col items-center justify-center p-2 rounded bg-emerald-500/10">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 mb-1" />
            <span className="text-sm font-medium text-emerald-700">{summary.pass_count}</span>
          </div>
          <div className="flex flex-col items-center justify-center p-2 rounded bg-amber-500/10">
            <AlertTriangle className="h-4 w-4 text-amber-600 mb-1" />
            <span className="text-sm font-medium text-amber-700">{summary.warning_count}</span>
          </div>
          <div className="flex flex-col items-center justify-center p-2 rounded bg-rose-500/10">
            <XCircle className="h-4 w-4 text-rose-600 mb-1" />
            <span className="text-sm font-medium text-rose-700">{summary.fail_count}</span>
          </div>
        </div>
        <div className="text-[10px] text-center text-muted-foreground mt-2 uppercase tracking-wider">
          Avg Score: {summary.average_score.toFixed(2)} • Runs: {summary.total_runs}
        </div>
      </CardContent>
    </Card>
  );
}
