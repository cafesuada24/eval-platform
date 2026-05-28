"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Save, Play } from "lucide-react"
import { PipelineMetricCard } from "@/components/pipelines/PipelineMetricCard"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { toast } from "sonner"

interface ThresholdConfig {
  fail_over?: number;
  fail_below?: number;
  warning_over?: number;
  warning_below?: number;
}

interface PipelineMetric {
  metric_name: string;
  threshold?: ThresholdConfig;
}

interface Pipeline {
  name: string;
  metrics: PipelineMetric[];
}

interface Metric {
  name: string;
  type: string;
}

interface Props {
  initialPipeline: Pipeline;
  availableMetrics: Metric[];
}

export function PipelineEditor({ initialPipeline, availableMetrics }: Props) {
  const [pipeline, setPipeline] = useState<Pipeline>(initialPipeline);
  const [isSaving, setIsSaving] = useState(false);

  const addMetric = (metricName: string) => {
    if (pipeline.metrics.some(m => m.metric_name === metricName)) {
      toast.error(`Metric ${metricName} is already in the pipeline`);
      return;
    }
    
    setPipeline({
      ...pipeline,
      metrics: [...pipeline.metrics, { metric_name: metricName, threshold: {} }]
    });
    toast.success(`Added ${metricName} to pipeline`);
  }
  
  const savePipeline = async () => {
    setIsSaving(true);
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE_URL}/v1/pipelines/${pipeline.name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pipeline)
      });
      if (!res.ok) throw new Error("Failed to save pipeline");
      toast.success("Pipeline saved successfully");
    } catch (error) {
      toast.error("Failed to save pipeline");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight text-foreground">{pipeline.name}</h1>
          <p className="text-muted-foreground text-lg max-w-2xl">
            Pipeline Configuration
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="border-border/50 bg-card/50 backdrop-blur-sm" onClick={savePipeline} disabled={isSaving}>
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? "Saving..." : "Save"}
          </Button>
          <Button className="bg-primary text-primary-foreground shadow-lg shadow-primary/20">
            <Play className="w-4 h-4 mr-2" />
            Run Evaluation
          </Button>
        </div>
      </div>

      <div className="mt-12 space-y-6">
        <div className="flex items-center justify-between border-b border-border/50 pb-4">
          <h2 className="text-2xl font-semibold tracking-tight">Active Metrics</h2>
          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 text-primary hover:text-primary hover:bg-primary/10 h-8 px-3">
              + Add Metric
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              {availableMetrics.length === 0 ? (
                <div className="p-2 text-sm text-muted-foreground">No metrics available</div>
              ) : (
                availableMetrics.map(m => (
                  <DropdownMenuItem key={m.name} onClick={() => addMetric(m.name)} className="cursor-pointer">
                    {m.name} <span className="ml-auto text-xs opacity-50">{m.type}</span>
                  </DropdownMenuItem>
                ))
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="grid gap-6">
          {pipeline.metrics.map((metric, index) => (
            <PipelineMetricCard
              key={`${metric.metric_name}-${index}`}
              name={metric.metric_name}
              description={`Semantic thresholds applied for ${metric.metric_name}`}
              type="custom"
            />
          ))}
          {pipeline.metrics.length === 0 && (
            <div className="text-center p-8 border border-dashed border-border/50 rounded-lg text-muted-foreground bg-card/10">
              No metrics added yet. Click "+ Add Metric" to start building your pipeline.
            </div>
          )}
        </div>
      </div>
    </>
  )
}
