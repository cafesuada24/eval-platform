import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
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

export function PipelineMetricCard({ name, description, model, type, scoringScale, threshold, onThresholdChange }: PipelineMetricCardProps) {
  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 shadow-sm overflow-hidden group hover:border-primary/30 transition-colors">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1.5">
            <CardTitle className="text-xl flex items-center gap-2">
              {name}
              <Badge 
                variant={type === "primitive" ? "secondary" : "default"}
                className={cn(
                  "rounded-[2px]",
                  type === "custom" ? "bg-primary/20 text-primary border-primary/30" : "font-normal"
                )}
              >
                {type}
              </Badge>
            </CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          {model && (
            <Badge variant="outline" className="font-mono text-xs opacity-70 rounded-[2px]">
              {model}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="bg-muted/10 pt-4 border-t border-border/30">
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-foreground/80">Semantic Thresholds</h4>
          <ThresholdBuilder value={threshold} onChange={onThresholdChange} scoringScale={scoringScale} />
        </div>
      </CardContent>
    </Card>
  )
}
