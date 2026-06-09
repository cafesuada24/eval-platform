"use client"

import Link from "next/link"
import { Pencil, LayoutList } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { DeleteMetricButton } from "@/components/metrics/delete-metric-button"
import { cn } from "@/lib/utils"
import { Metric } from "@/lib/types"

interface MetricDetailProps {
  metric: Metric | null
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
      {children}
    </h4>
  )
}

function StatWidget({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-muted/30 rounded-[2px] p-3 text-center border border-border/30">
      <p className="text-[10px] text-muted-foreground mb-1">{label}</p>
      <p className="text-base font-bold font-mono">{value}</p>
    </div>
  )
}

export function MetricDetail({ metric }: MetricDetailProps) {
  if (!metric) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
        <LayoutList className="w-10 h-10 opacity-20" />
        <p className="text-sm">Select a metric to view details</p>
      </div>
    )
  }

  const isAiJudge = metric.type === "ai-judge"

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-bold tracking-tight">{metric.name}</h2>
            <Badge
              variant={isAiJudge ? "default" : "secondary"}
              className={cn(
                "text-[10px] rounded-[2px] font-mono",
                isAiJudge ? "bg-primary/15 text-primary border-primary/20" : ""
              )}
            >
              {metric.type}
            </Badge>
          </div>
          {metric.description && (
            <p className="text-sm text-muted-foreground leading-relaxed">
              {metric.description}
            </p>
          )}
        </div>

        <Separator className="opacity-40" />

        {/* Scoring Scale */}
        {metric.scoring_scale && (
          <section className="space-y-3">
            <SectionLabel>Scoring Scale</SectionLabel>
            <div className="grid grid-cols-3 gap-3">
              <StatWidget label="Min" value={metric.scoring_scale.min} />
              <StatWidget label="Max" value={metric.scoring_scale.max} />
              <StatWidget label="Type" value={metric.scoring_scale.data_type} />
            </div>
          </section>
        )}

        {/* Required Inputs */}
        {metric.required_inputs && metric.required_inputs.length > 0 && (
          <>
            <Separator className="opacity-40" />
            <section className="space-y-3">
              <SectionLabel>Required Inputs</SectionLabel>
              <div className="flex flex-wrap gap-1.5">
                {metric.required_inputs.map((input) => (
                  <Badge
                    key={input}
                    variant="outline"
                    className="font-mono text-[11px] rounded-[2px]"
                  >
                    {`{{${input}}}`}
                  </Badge>
                ))}
              </div>
            </section>
          </>
        )}

        {/* Model Config (AI Judge only) */}
        {isAiJudge && metric.model_configuration && (
          <>
            <Separator className="opacity-40" />
            <section className="space-y-3">
              <SectionLabel>Model Configuration</SectionLabel>
              <div className="space-y-1.5 text-xs">
                {[
                  { label: "Provider", value: metric.model_configuration.provider },
                  { label: "Model", value: metric.model_configuration.model },
                  { label: "Temperature", value: metric.model_configuration.temperature },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="flex justify-between items-center py-1.5 border-b border-border/30 last:border-0"
                  >
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-mono">{value}</span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}

        {/* Prompt Template (AI Judge only) */}
        {isAiJudge && metric.prompt_template && (
          <>
            <Separator className="opacity-40" />
            <section className="space-y-3">
              <SectionLabel>Prompt Template</SectionLabel>
              <pre className="text-xs font-mono bg-muted/30 p-3 rounded-[2px] whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto border border-border/30">
                {metric.prompt_template}
              </pre>
            </section>
          </>
        )}

        {/* Actions */}
        <Separator className="opacity-40" />
        <div className="flex gap-2">
          {isAiJudge ? (
            <>
              <Link href={`/playground?metric=${metric.name}`} className="flex-1">
                <Button size="sm" className="w-full rounded-[2px] gap-2">
                  <Pencil className="w-3.5 h-3.5" />
                  Edit in Playground
                </Button>
              </Link>
              <DeleteMetricButton metricId={metric.id} metricName={metric.name} />
            </>
          ) : (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger render={<span className="flex-1" />}>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled
                    className="w-full rounded-[2px] opacity-50 cursor-not-allowed"
                  >
                    System metric — read only
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Primitive metrics cannot be edited or deleted</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </div>
    </div>
  )
}
