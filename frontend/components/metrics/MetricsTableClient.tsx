"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Pencil } from "lucide-react"
import { DeleteMetricButton } from "@/components/metrics/delete-metric-button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import Link from "next/link"
import { Metric } from "@/lib/types"
import { cn } from "@/lib/utils"

interface MetricsTableClientProps {
  metrics: Metric[]
}

function MetricPreviewSheet({ metric, open, onClose }: { metric: Metric | null; open: boolean; onClose: () => void }) {
  if (!metric) return null

  const isAiJudge = metric.type === "ai-judge"

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[420px] sm:w-[500px] overflow-y-auto">
        <SheetHeader className="pb-4">
          <div className="flex items-center gap-2 flex-wrap">
            <SheetTitle className="text-base">{metric.name}</SheetTitle>
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
            <SheetDescription className="text-sm leading-relaxed">
              {metric.description}
            </SheetDescription>
          )}
        </SheetHeader>

        <div className="space-y-5 pt-2">
          {/* Scoring Scale */}
          {metric.scoring_scale && (
            <section className="space-y-2">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Scoring Scale</h4>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-muted/30 rounded-[2px] p-3 text-center">
                  <p className="text-xs text-muted-foreground mb-1">Min</p>
                  <p className="text-lg font-bold font-mono">{metric.scoring_scale.min}</p>
                </div>
                <div className="bg-muted/30 rounded-[2px] p-3 text-center">
                  <p className="text-xs text-muted-foreground mb-1">Max</p>
                  <p className="text-lg font-bold font-mono">{metric.scoring_scale.max}</p>
                </div>
                <div className="bg-muted/30 rounded-[2px] p-3 text-center">
                  <p className="text-xs text-muted-foreground mb-1">Type</p>
                  <p className="text-sm font-mono font-medium">{metric.scoring_scale.data_type}</p>
                </div>
              </div>
            </section>
          )}

          {/* Required Inputs */}
          {metric.required_inputs && metric.required_inputs.length > 0 && (
            <section className="space-y-2">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Required Inputs</h4>
              <div className="flex flex-wrap gap-1.5">
                {metric.required_inputs.map((input) => (
                  <Badge
                    key={input}
                    variant="outline"
                    className="font-mono text-xs rounded-[2px]"
                  >
                    {"{{"}{input}{"}}"}
                  </Badge>
                ))}
              </div>
            </section>
          )}

          {/* Model Config */}
          {metric.model_configuration && (
            <>
              <Separator className="opacity-50" />
              <section className="space-y-2">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Model Configuration</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center py-1 border-b border-border/30">
                    <span className="text-muted-foreground text-xs">Provider</span>
                    <span className="font-mono text-xs">{metric.model_configuration.provider}</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-border/30">
                    <span className="text-muted-foreground text-xs">Model</span>
                    <span className="font-mono text-xs">{metric.model_configuration.model}</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span className="text-muted-foreground text-xs">Temperature</span>
                    <span className="font-mono text-xs">{metric.model_configuration.temperature}</span>
                  </div>
                </div>
              </section>
            </>
          )}

          {/* Prompt Template */}
          {metric.prompt_template && (
            <>
              <Separator className="opacity-50" />
              <section className="space-y-2">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Prompt Template</h4>
                <pre className="text-xs font-mono bg-muted/30 p-3 rounded-[2px] whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto border border-border/30">
                  {metric.prompt_template}
                </pre>
              </section>
            </>
          )}

          {/* Actions */}
          <Separator className="opacity-50" />
          <div className="flex gap-2 pt-1">
            {isAiJudge ? (
              <Link href={`/playground?metric=${metric.name}`} className="flex-1">
                <Button size="sm" className="w-full rounded-[2px] gap-2">
                  <Pencil className="w-3.5 h-3.5" />
                  Edit in Playground
                </Button>
              </Link>
            ) : (
              <Button size="sm" variant="outline" disabled className="flex-1 rounded-[2px] opacity-50 cursor-not-allowed">
                System metric — read only
              </Button>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

function GroupHeader({ label, count }: { label: string; count: number }) {
  return (
    <TableRow className="hover:bg-transparent border-border/30">
      <TableCell colSpan={4} className="py-2 px-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
            {label}
          </span>
          <span className="text-[10px] text-muted-foreground/40 font-mono">{count}</span>
          <div className="flex-1 h-px bg-border/30" />
        </div>
      </TableCell>
    </TableRow>
  )
}

function MetricRow({
  metric,
  onPreview,
}: {
  metric: Metric
  onPreview: (metric: Metric) => void
}) {
  const isAiJudge = metric.type === "ai-judge"

  return (
    <TableRow
      className="border-border/50 transition-colors hover:bg-muted/30 group cursor-pointer"
      onClick={() => onPreview(metric)}
    >
      <TableCell className="font-medium max-w-[300px] sm:max-w-[400px]">
        <div className="flex flex-col gap-1.5">
          <span className="truncate hover:text-primary transition-colors" title={metric.name}>
            {metric.name}
          </span>
          <span className="text-xs text-muted-foreground font-normal truncate" title={metric.description}>
            {metric.description}
          </span>
        </div>
      </TableCell>
      <TableCell>
        <Badge
          variant={isAiJudge ? "default" : "secondary"}
          className={cn(
            "rounded-[2px]",
            isAiJudge ? "bg-primary/10 text-primary hover:bg-primary/20 border-primary/20" : ""
          )}
        >
          {metric.type}
        </Badge>
      </TableCell>
      <TableCell className="font-mono text-xs text-muted-foreground">
        {metric.model_configuration?.model || '-'}
      </TableCell>
      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-end gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
          {!isAiJudge ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger render={<span tabIndex={0} className="inline-block cursor-not-allowed" />}>
                  <Button variant="ghost" size="icon" disabled className="opacity-50 pointer-events-none">
                    <Pencil className="w-4 h-4" />
                    <span className="sr-only">Edit</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="bg-secondary text-secondary-foreground border-border/50">
                  <p>System metrics cannot be edited</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger render={<span tabIndex={0} className="inline-block cursor-not-allowed" />}>
                  <DeleteMetricButton metricId={metric.id} metricName={metric.name} disabled />
                </TooltipTrigger>
                <TooltipContent className="bg-secondary text-secondary-foreground border-border/50">
                  <p>System metrics cannot be deleted</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <>
              <Link href={`/playground?metric=${metric.name}`}>
                <Button variant="ghost" size="icon" className="hover:text-primary hover:bg-primary/10">
                  <Pencil className="w-4 h-4" />
                  <span className="sr-only">Edit</span>
                </Button>
              </Link>
              <DeleteMetricButton metricId={metric.id} metricName={metric.name} />
            </>
          )}
        </div>
      </TableCell>
    </TableRow>
  )
}

export function MetricsTableClient({ metrics }: MetricsTableClientProps) {
  const [previewMetric, setPreviewMetric] = useState<Metric | null>(null)

  const primitives = metrics.filter((m) => m.type === "primitive")
  const aiJudges = metrics.filter((m) => m.type === "ai-judge")

  return (
    <>
      <div className="border border-border/40 rounded-[2px] bg-card/30 backdrop-blur-xs flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <Table>
            <TableHeader className="bg-muted/50 sticky top-0 z-10 backdrop-blur-md">
              <TableRow className="hover:bg-transparent border-border/50">
                <TableHead className="w-[40%] sm:w-[50%] min-w-[250px]">Name & Description</TableHead>
                <TableHead className="w-[15%] min-w-[100px]">Type</TableHead>
                <TableHead className="w-[20%] min-w-[120px]">Model</TableHead>
                <TableHead className="w-[15%] min-w-[100px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {metrics.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-48 text-center text-muted-foreground">
                    No metrics found matching your criteria.
                  </TableCell>
                </TableRow>
              ) : (
                <>
                  {primitives.length > 0 && (
                    <>
                      <GroupHeader label="Primitive" count={primitives.length} />
                      {primitives.map((metric, index) => (
                        <MetricRow
                          key={metric.id || metric.name || index}
                          metric={metric}
                          onPreview={setPreviewMetric}
                        />
                      ))}
                    </>
                  )}
                  {aiJudges.length > 0 && (
                    <>
                      <GroupHeader label="AI Judge" count={aiJudges.length} />
                      {aiJudges.map((metric, index) => (
                        <MetricRow
                          key={metric.id || metric.name || index}
                          metric={metric}
                          onPreview={setPreviewMetric}
                        />
                      ))}
                    </>
                  )}
                </>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <MetricPreviewSheet
        metric={previewMetric}
        open={!!previewMetric}
        onClose={() => setPreviewMetric(null)}
      />
    </>
  )
}
