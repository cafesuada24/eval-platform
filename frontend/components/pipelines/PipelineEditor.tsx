"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Save, Play, X, Pencil } from "lucide-react"
import { PipelineMetricCard } from "@/components/pipelines/PipelineMetricCard"
import { MetricSelectorSheet } from "@/components/pipelines/MetricSelectorSheet"
import { toast } from "sonner"
import { cn, getApiBaseUrl } from "@/lib/utils"

import { Pipeline, Metric } from "@/lib/types"
import { Thresholds } from "@/components/pipelines/ThresholdBuilder"

interface Props {
  initialPipeline: Pipeline;
  availableMetrics: Metric[];
}

import { useRouter } from "next/navigation"
import { useRef } from "react"

export function PipelineEditor({ initialPipeline, availableMetrics }: Props) {
  const router = useRouter();
  const [pipeline, setPipeline] = useState<Pipeline>(initialPipeline);
  const [isSaving, setIsSaving] = useState(false);
  const [isTitleFocused, setIsTitleFocused] = useState(false);
  const [baseline, setBaseline] = useState(() => JSON.stringify(initialPipeline));
  const titleRef = useRef<HTMLInputElement>(null);

  // Derive dirty state from stable baseline stored in state (not a ref, safe to read during render)
  const isDirty = JSON.stringify(pipeline) !== baseline;

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
      const API_BASE_URL = getApiBaseUrl();
      
      const url = isNew 
        ? `${API_BASE_URL}/v1/configs/pipelines`
        : `${API_BASE_URL}/v1/configs/pipelines/${pipeline.id}`;
        
      const payload: Omit<Pipeline, "id"> & { id?: string } = { ...pipeline };
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
      setBaseline(JSON.stringify(pipeline));

      if (isNew && saved.id) {
        router.replace(`/pipelines/${saved.id}`);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to save pipeline";
      console.error("Save error:", error);
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div className="flex-1 min-w-0 space-y-1">
          {/* Editable title */}
          <div
            className={cn(
              "group relative flex items-center gap-2 rounded-md -ml-2 px-2 py-1 transition-colors",
              isTitleFocused ? "bg-muted/30 ring-1 ring-primary/30" : "hover:bg-muted/20"
            )}
          >
            <input
              ref={titleRef}
              type="text"
              className="text-3xl font-bold tracking-tight text-foreground bg-transparent border-none focus:outline-none w-full min-w-0"
              value={pipeline.name}
              onChange={(e) => setPipeline({ ...pipeline, name: e.target.value })}
              onFocus={() => setIsTitleFocused(true)}
              onBlur={() => setIsTitleFocused(false)}
              placeholder="Pipeline Name"
            />
            <Pencil
              className={cn(
                "w-4 h-4 text-muted-foreground shrink-0 transition-opacity",
                isTitleFocused ? "opacity-60" : "opacity-0 group-hover:opacity-40"
              )}
            />
          </div>

          {/* Metric count + dirty badge */}
          <div className="flex items-center gap-2 ml-1">
            <span className="text-sm text-muted-foreground">
              {pipeline.metrics.length === 0
                ? "No metrics configured"
                : `${pipeline.metrics.length} metric${pipeline.metrics.length !== 1 ? "s" : ""} configured`}
            </span>
            {isDirty && (
              <span className="inline-flex items-center gap-1 text-[10px] font-mono text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-[2px] px-1.5 py-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" />
                Unsaved changes
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 shrink-0">
          <Button
            variant="outline"
            className="border-border/50 bg-card/50 backdrop-blur-sm"
            onClick={savePipeline}
            disabled={isSaving}
          >
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? "Saving..." : "Save"}
          </Button>
          <Button className="bg-primary text-primary-foreground shadow-lg shadow-primary/20">
            <Play className="w-4 h-4 mr-2" />
            Run Evaluation
          </Button>
        </div>
      </div>

      {/* Metrics section */}
      <div className="mt-10 space-y-6">
        <div className="flex items-center justify-between border-b border-border/50 pb-4">
          <h2 className="text-xl font-semibold tracking-tight">Active Metrics</h2>
          <MetricSelectorSheet
            availableMetrics={availableMetrics}
            addedMetricIds={pipeline.metrics.map(m => m.metric_id)}
            onAdd={addMetric}
          />
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
                  threshold={item.threshold as Thresholds}
                  onThresholdChange={(newThreshold) => {
                    const newMetrics = [...pipeline.metrics];
                    newMetrics[index] = { ...newMetrics[index], threshold: newThreshold };
                    setPipeline({ ...pipeline, metrics: newMetrics });
                  }}
                />
                <Button
                  variant="destructive"
                  size="icon"
                  className="absolute -top-3 -right-3 h-7 w-7 rounded-full opacity-0 group-hover:opacity-100 transition-opacity z-10 shadow-md"
                  onClick={() => removeMetric(index)}
                  title="Remove metric"
                >
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            );
          })}
          {pipeline.metrics.length === 0 && (
            <div className="text-center p-10 border border-dashed border-border/50 rounded-[2px] text-muted-foreground bg-card/10 space-y-2">
              <p className="text-sm">No metrics added yet.</p>
              <p className="text-xs opacity-70">Click <strong>+ Add Metric</strong> above to start building your pipeline.</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
