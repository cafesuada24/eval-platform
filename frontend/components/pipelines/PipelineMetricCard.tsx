"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronDown } from "lucide-react"
import { ThresholdBuilder, Thresholds } from "./ThresholdBuilder"
import { Metric } from "@/lib/types"
import { cn } from "@/lib/utils"

interface PipelineMetricCardProps {
  name: string
  description: string
  model?: string
  type: "primitive" | "custom"
  scoringScale?: Metric["scoring_scale"]
  threshold?: Thresholds
  onThresholdChange?: (threshold: Thresholds) => void
}

export function PipelineMetricCard({
  name,
  description,
  model,
  type,
  scoringScale,
  threshold,
  onThresholdChange,
}: PipelineMetricCardProps) {
  const [thresholdOpen, setThresholdOpen] = useState(true)

  const hasRules =
    threshold &&
    Object.values(threshold).some((v) => v !== null && v !== undefined)

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 shadow-sm overflow-hidden group hover:border-primary/30 transition-colors">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1.5 flex-1 min-w-0">
            <CardTitle className="text-lg flex items-center gap-2 flex-wrap">
              <span className="truncate">{name}</span>
              <Badge
                variant={type === "primitive" ? "secondary" : "default"}
                className={cn(
                  "rounded-[2px] shrink-0",
                  type === "custom"
                    ? "bg-primary/20 text-primary border-primary/30"
                    : "font-normal"
                )}
              >
                {type}
              </Badge>
            </CardTitle>
            <CardDescription className="text-xs">{description}</CardDescription>
          </div>
          {model && (
            <Badge variant="outline" className="font-mono text-xs opacity-70 rounded-[2px] shrink-0">
              {model}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="pt-0 pb-0">
        {/* Collapsible threshold section */}
        <button
          type="button"
          onClick={() => setThresholdOpen((v) => !v)}
          className="w-full flex items-center justify-between py-3 px-0 border-t border-border/30 text-left group/toggle"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-foreground/70">Semantic Thresholds</span>
            {hasRules && (
              <span className="text-[10px] font-mono text-muted-foreground/50">
                ({Object.values(threshold!).filter((v) => v !== undefined).length} rule
                {Object.values(threshold!).filter((v) => v !== undefined).length !== 1 ? "s" : ""})
              </span>
            )}
          </div>
          <ChevronDown
            className={cn(
              "w-3.5 h-3.5 text-muted-foreground transition-transform",
              thresholdOpen ? "rotate-0" : "-rotate-90"
            )}
          />
        </button>

        {thresholdOpen && (
          <div className="pb-4">
            <ThresholdBuilder
              value={threshold}
              onChange={onThresholdChange}
              scoringScale={scoringScale}
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
