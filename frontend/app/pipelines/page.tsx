import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ListTree, Plus, Settings2 } from "lucide-react"
import { PipelineCardMenu } from "@/components/pipelines/PipelineCardMenu"

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

import { Pipeline } from "@/lib/types"

async function getPipelines(): Promise<Pipeline[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/configs/pipelines`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch pipelines:", error);
    return [];
  }
}

import { PageHeader } from "@/components/ui/page-header"

export default async function PipelinesPage() {
  const pipelines = await getPipelines();
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 bg-background">
      <PageHeader
        preTitle="Evaluation Core"
        title="Observability Pipelines"
        description="Configure automated evaluation rulesets and thresholds."
        actions={
          <Link href="/pipelines/new">
            <Button size="sm" className="h-9 rounded-[2px] shadow-sm">
              <Plus className="w-4 h-4 mr-2" />
              New Pipeline
            </Button>
          </Link>
        }
      />

      {pipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-16 border border-dashed border-border/40 rounded-[2px] bg-card/10">
          <div className="w-14 h-14 rounded-full bg-muted/50 flex items-center justify-center mb-4">
            <ListTree className="w-7 h-7 text-muted-foreground opacity-60" />
          </div>
          <h3 className="text-base font-semibold">No pipelines yet</h3>
          <p className="text-sm text-muted-foreground mt-1.5 mb-6 text-center max-w-sm leading-relaxed">
            Create your first observability pipeline to start evaluating traces and tracking semantic thresholds over time.
          </p>
          <Link href="/pipelines/new">
            <Button size="sm" className="rounded-[2px] gap-2">
              <Plus className="w-4 h-4" />
              Create your first pipeline
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {pipelines.map((pipeline, index) => {
            const metricCount = pipeline.metrics?.length || 0;
            return (
              <Card
                key={`${pipeline.id || pipeline.name}-${index}`}
                className="hover:border-primary/30 transition-colors bg-card/30 border-border/40 rounded-[2px] shadow-sm group relative overflow-hidden"
              >
                {/* Subtle left accent bar */}
                <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary/0 group-hover:bg-primary/40 transition-colors rounded-l-[2px]" />

                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <Link
                      href={`/pipelines/${pipeline.id || pipeline.name}`}
                      className="flex-1 min-w-0"
                    >
                      <CardTitle className="group-hover:text-primary transition-colors text-base flex items-center gap-2 truncate">
                        <Settings2 className="w-4 h-4 text-muted-foreground shrink-0 opacity-60" />
                        <span className="truncate">{pipeline.name}</span>
                      </CardTitle>
                    </Link>
                    <PipelineCardMenu pipelineId={pipeline.id} pipelineName={pipeline.name} />
                  </div>

                  <div className="flex items-center gap-2 mt-2 ml-6">
                    {metricCount === 0 ? (
                      <Badge
                        variant="outline"
                        className="text-[10px] font-mono rounded-[2px] text-amber-500 border-amber-500/30 bg-amber-500/5"
                      >
                        No metrics configured
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="text-[10px] font-mono rounded-[2px] text-emerald-600 border-emerald-500/30 bg-emerald-500/5"
                      >
                        {metricCount} metric{metricCount !== 1 ? "s" : ""} configured
                      </Badge>
                    )}
                  </div>

                  <CardDescription className="ml-6 text-xs mt-1">
                    Click to configure metrics and thresholds
                  </CardDescription>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  )
}
