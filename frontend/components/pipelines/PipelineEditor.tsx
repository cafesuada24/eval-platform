"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Save, Play, X } from "lucide-react"
import { PipelineMetricCard } from "@/components/pipelines/PipelineMetricCard"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { toast } from "sonner"

import { Pipeline, Metric } from "@/lib/types"

interface Props {
  initialPipeline: Pipeline;
  availableMetrics: Metric[];
}

import { useRouter } from "next/navigation"

export function PipelineEditor({ initialPipeline, availableMetrics }: Props) {
  const router = useRouter();
  const [pipeline, setPipeline] = useState<Pipeline>(initialPipeline);
  const [isSaving, setIsSaving] = useState(false);

  const addMetric = (metricName: string) => {
    const selectedMetric = availableMetrics.find(m => m.name === metricName);
    if (!selectedMetric) return;

    if (pipeline.metrics.some(m => m.metric_id === selectedMetric.id)) {
      toast.error(`Metric ${metricName} is already in the pipeline`);
      return;
    }
    
    setPipeline({
      ...pipeline,
      metrics: [...pipeline.metrics, { metric_id: selectedMetric.id, threshold: {} }]
    });
    toast.success(`Added ${metricName} to pipeline`);
  }

  const removeMetric = (index: number) => {
    const newMetrics = [...pipeline.metrics];
    newMetrics.splice(index, 1);
    setPipeline({
      ...pipeline,
      metrics: newMetrics
    });
  }
  
  const savePipeline = async () => {
    // Validate thresholds against metric scoring_scale before submitting
    for (const item of pipeline.metrics) {
      const metricDetails = availableMetrics.find(m => m.id === item.metric_id);
      if (!metricDetails || !item.threshold) continue;
      
      const scale = metricDetails.scoring_scale;
      for (const [key, val] of Object.entries(item.threshold)) {
        if (val === null || val === undefined) continue;
        
        if (val < scale.min || val > scale.max) {
          toast.error(`Validation Error in ${metricDetails.name}`, {
            description: `${key} (${val}) must be between ${scale.min} and ${scale.max}.`
          });
          return;
        }
        
        if (scale.data_type === "integer" && !Number.isInteger(val)) {
          toast.error(`Validation Error in ${metricDetails.name}`, {
            description: `${key} must be a whole number (integer).`
          });
          return;
        }
      }
    }

    setIsSaving(true);
    try {
      const isNew = !pipeline.id;
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      const url = isNew 
        ? `${API_BASE_URL}/v1/configs/pipelines`
        : `${API_BASE_URL}/v1/configs/pipelines/${pipeline.id}`;
        
      const payload: any = { ...pipeline };
      if (isNew) delete payload.id;

      const res = await fetch(url, {
        method: isNew ? 'POST' : 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const errorMessage = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : JSON.stringify(errorData.detail || "Failed to save pipeline");
        throw new Error(errorMessage);
      }
      
      const saved = await res.json();
      toast.success("Pipeline saved successfully");
      
      if (isNew && saved.id) {
        router.replace(`/pipelines/${saved.id}`);
      }
    } catch (error: any) {
      console.error("Save error:", error);
      toast.error(error.message || "Failed to save pipeline");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      <div className="flex items-start justify-between">
        <div className="space-y-2 w-full max-w-2xl mr-4">
          <input
            type="text"
            className="text-4xl font-bold tracking-tight text-foreground bg-transparent border-none focus:outline-none focus:ring-2 focus:ring-primary/50 rounded-md px-2 -ml-2 w-full"
            value={pipeline.name}
            onChange={(e) => setPipeline({ ...pipeline, name: e.target.value })}
            placeholder="Pipeline Name"
          />
          <p className="text-muted-foreground text-lg ml-1">
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
          {pipeline.metrics.map((item, index) => {
            const metricDetails = availableMetrics.find(m => m.id === item.metric_id);
            if (!metricDetails) return null;
            return (
              <div key={`${metricDetails.name}-${index}`} className="relative group">
                <PipelineMetricCard
                  name={metricDetails.name}
                  description={`Semantic thresholds applied for ${metricDetails.name}`}
                  type={metricDetails.type === "ai-judge" ? "custom" : metricDetails.type}
                  scoringScale={metricDetails.scoring_scale}
                  threshold={item.threshold as any}
                  onThresholdChange={(newThreshold) => {
                    const newMetrics = [...pipeline.metrics];
                    newMetrics[index] = { ...newMetrics[index], threshold: newThreshold };
                    setPipeline({ ...pipeline, metrics: newMetrics });
                  }}
                />
                <Button 
                  variant="destructive" 
                  size="icon" 
                  className="absolute -top-3 -right-3 h-8 w-8 rounded-full opacity-0 group-hover:opacity-100 transition-opacity z-10"
                  onClick={() => removeMetric(index)}
                  title="Remove metric"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            );
          })}
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
