import Link from "next/link";
import { getEvaluations } from "@/lib/api/evaluations";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  ListTree, 
  Activity, 
  Database, 
  Bot, 
  ArrowRight, 
  ChevronRight
} from "lucide-react";
import { Metric, Pipeline } from "@/lib/types";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getPipelines(): Promise<Pipeline[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/configs/pipelines`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch pipelines on home dashboard:", error);
    return [];
  }
}

async function getMetrics(): Promise<Metric[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/configs/metrics`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch metrics on home dashboard:", error);
    return [];
  }
}

async function getDatasets() {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/datasets/`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch datasets on home dashboard:", error);
    return [];
  }
}

function formatDate(dateStr?: string) {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    const pad = (num: number) => String(num).padStart(2, "0");
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
  } catch (e) {
    return "-";
  }
}

export default async function Home() {
  const [pipelines, metrics, datasets, evaluations] = await Promise.all([
    getPipelines(),
    getMetrics(),
    getDatasets(),
    getEvaluations().catch(() => [])
  ]);

  const aiJudges = metrics.filter(m => m.type === "ai-judge").length;
  const primitives = metrics.filter(m => m.type === "primitive").length;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 min-h-[calc(100vh-3.5rem)] bg-background">
      {/* Header Section */}
      <div className="flex flex-col gap-2 pb-6 border-b border-border/40">
        <p className="text-xs font-semibold text-primary uppercase tracking-widest font-mono">
          System Control Panel
        </p>
        <h1 className="text-4xl font-extrabold tracking-tighter text-foreground">
          EvalPlatform Dashboard
        </h1>
        <p className="text-sm text-muted-foreground max-w-2xl">
          Observe pipeline execution, semantic thresholds, and configure real-time AI judges.
        </p>
      </div>

      {/* Grid Layout - Asymmetric Swiss Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
        {/* Left Columns (3/5 width): Overview & Recent Evaluations */}
        <div className="lg:col-span-3 space-y-6">
          {/* Telemetry Stats */}
          <div className="grid grid-cols-3 gap-4">
            <Card className="bg-card/30 border-border/50 hover:border-border transition-colors">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground uppercase">Pipelines</span>
                  <ListTree className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="mt-4 flex items-baseline gap-2">
                  <span className="text-3xl font-bold tracking-tight">{pipelines.length}</span>
                  <span className="text-xs text-muted-foreground">active</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/30 border-border/50 hover:border-border transition-colors">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground uppercase">Metrics</span>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="mt-4 flex items-baseline gap-2">
                  <span className="text-3xl font-bold tracking-tight">{metrics.length}</span>
                  <span className="text-xs text-muted-foreground font-mono">
                    {aiJudges} judge / {primitives} prim
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/30 border-border/50 hover:border-border transition-colors">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground uppercase">Datasets</span>
                  <Database className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="mt-4 flex items-baseline gap-2">
                  <span className="text-3xl font-bold tracking-tight">{datasets.length}</span>
                  <span className="text-xs text-muted-foreground font-mono">stores</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Evaluations Runs list */}
          <Card className="bg-card/20 border-border/50 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/30">
              <div>
                <CardTitle className="text-sm font-semibold tracking-tight uppercase font-mono">Recent Batch runs</CardTitle>
                <CardDescription className="text-xs">Observe latest evaluation logs and target pass rates.</CardDescription>
              </div>
              <Link href="/evaluations">
                <Button variant="ghost" size="sm" className="h-8 text-xs font-mono uppercase tracking-wider">
                  View All Runs
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border/30">
                {evaluations.length === 0 ? (
                  <div className="p-12 text-center text-muted-foreground font-mono text-xs italic">
                    No evaluations run logs available.
                  </div>
                ) : (
                  evaluations.slice(0, 5).map((run: any) => {
                    const passRate = run.pass_rate || 0;
                    return (
                      <div key={run.job_id} className="p-4 flex items-center justify-between hover:bg-muted/10 transition-colors group relative">
                        <Link href={`/evaluations/${run.job_id}`} className="absolute inset-0 z-10">
                          <span className="sr-only">View run details</span>
                        </Link>
                        <div className="flex items-center gap-4">
                          <div className="flex flex-col gap-1">
                            <span className="font-mono text-xs font-semibold text-foreground/90">
                              {run.job_id.split("-")[0]}...
                            </span>
                            <span className="text-[10px] text-muted-foreground font-mono">
                              {formatDate(run.created_at)}
                            </span>
                          </div>
                          <div className="hidden sm:flex flex-col gap-0.5">
                            <span className="text-xs text-muted-foreground">Pipeline / Dataset</span>
                            <span className="text-xs font-medium truncate max-w-[180px]">
                              {run.pipeline_name || run.pipeline_id} / {run.dataset_name || run.dataset_id}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-6">
                          {/* Pass rate visualization */}
                          <div className="flex flex-col items-end gap-1">
                            <span className="text-[10px] font-mono text-muted-foreground uppercase">Pass Rate</span>
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1 bg-muted rounded-[1px] overflow-hidden border border-border/20">
                                <div 
                                  className={`h-full rounded-[1px] ${
                                    passRate >= 80 ? "bg-emerald-500" : passRate >= 50 ? "bg-amber-500" : "bg-rose-500"
                                  }`}
                                  style={{ width: `${passRate}%` }}
                                />
                              </div>
                              <span className="text-xs font-mono font-semibold text-foreground/80 w-8 text-right">
                                {passRate.toFixed(0)}%
                              </span>
                            </div>
                          </div>

                          <Badge 
                            variant="secondary" 
                            className={`rounded-[2px] font-mono text-[9px] font-semibold uppercase ${
                              run.status === "COMPLETED" 
                                ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20" 
                                : run.status === "FAILED" 
                                ? "bg-rose-500/10 text-rose-600 border border-rose-500/20" 
                                : "bg-blue-500/10 text-blue-600 border border-blue-500/20"
                            }`}
                          >
                            {run.status}
                          </Badge>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Columns (2/5 width): Console Quick Actions & Config */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-card/20 border-border/50">
            <CardHeader className="pb-3 border-b border-border/30">
              <CardTitle className="text-sm font-semibold tracking-tight uppercase font-mono">Control Console</CardTitle>
              <CardDescription className="text-xs">Quick setup triggers for pipeline components.</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <Link href="/playground" className="block">
                <div className="p-4 rounded-[2px] border border-border/50 bg-card/30 hover:border-primary/50 transition-all cursor-pointer group flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Bot className="h-4 w-4 text-primary" />
                      <span className="font-semibold text-xs uppercase tracking-wider">AI Judge Playground</span>
                    </div>
                    <p className="text-xs text-muted-foreground">Draft and debug custom LLM-as-a-judge metrics with the interactive agent.</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all shrink-0 mt-0.5" />
                </div>
              </Link>

              <Link href="/pipelines/new" className="block">
                <div className="p-4 rounded-[2px] border border-border/50 bg-card/30 hover:border-primary/50 transition-all cursor-pointer group flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <ListTree className="h-4 w-4 text-primary" />
                      <span className="font-semibold text-xs uppercase tracking-wider">Configure Pipeline</span>
                    </div>
                    <p className="text-xs text-muted-foreground">Chain evaluation metrics and specify warning/critical assertion thresholds.</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all shrink-0 mt-0.5" />
                </div>
              </Link>

              <Link href="/datasets" className="block">
                <div className="p-4 rounded-[2px] border border-border/50 bg-card/30 hover:border-primary/50 transition-all cursor-pointer group flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Database className="h-4 w-4 text-primary" />
                      <span className="font-semibold text-xs uppercase tracking-wider">Data Core Ingestion</span>
                    </div>
                    <p className="text-xs text-muted-foreground">Manage and upload test case datasets for batch evaluation pipelines.</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all shrink-0 mt-0.5" />
                </div>
              </Link>
            </CardContent>
          </Card>

          <Card className="bg-card/20 border-border/50">
            <CardHeader className="pb-3 border-b border-border/30">
              <CardTitle className="text-sm font-semibold tracking-tight uppercase font-mono">Status Board</CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-muted-foreground">AGENT CONNECTIVITY</span>
                <span className="text-emerald-500 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  ONLINE
                </span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono border-t border-border/30 pt-3">
                <span className="text-muted-foreground">PIPELINE JOBS</span>
                <span className="text-foreground/80">{pipelines.length} Configured</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono border-t border-border/30 pt-3">
                <span className="text-foreground/80">{metrics.length} Loaded</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono border-t border-border/30 pt-3">
                <span className="text-muted-foreground">API INTEGRATION</span>
                <span className="text-emerald-500 flex items-center gap-1">
                  HTTP (WEBSOCKET READY)
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
