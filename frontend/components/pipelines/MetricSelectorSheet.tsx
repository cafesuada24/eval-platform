"use client"

import { useState } from "react"
import { Plus, Search, Check, Cpu, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { Metric } from "@/lib/types"

interface MetricSelectorSheetProps {
  availableMetrics: Metric[]
  addedMetricIds: string[]
  onAdd: (metricName: string) => void
}

export function MetricSelectorSheet({ availableMetrics, addedMetricIds, onAdd }: MetricSelectorSheetProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")

  const filter = (metrics: Metric[]) =>
    metrics.filter(
      (m) =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        m.description?.toLowerCase().includes(search.toLowerCase())
    )

  const primitives = filter(availableMetrics.filter((m) => m.type === "primitive"))
  const aiJudges = filter(availableMetrics.filter((m) => m.type === "ai-judge"))
  const all = filter(availableMetrics)

  const handleAdd = (metricName: string) => {
    onAdd(metricName)
    // Don't close — let user add multiple
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 rounded-[2px] border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50 font-medium"
          />
        }
      >
        <Plus className="w-3.5 h-3.5" />
        Add Metric
      </SheetTrigger>

      <SheetContent className="w-[420px] sm:w-[480px] flex flex-col gap-0 p-0">
        <SheetHeader className="px-6 pt-6 pb-4 border-b border-border/50">
          <SheetTitle className="text-base">Add Metrics</SheetTitle>
          <SheetDescription className="text-xs">
            Select metrics to include in this pipeline. Click a metric to add it — you can add multiple.
          </SheetDescription>
          <div className="relative mt-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              placeholder="Search metrics..."
              className="pl-8 h-8 text-sm rounded-[2px] bg-muted/30 border-border/50"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
        </SheetHeader>

        <Tabs defaultValue="all" className="flex flex-col flex-1 overflow-hidden">
          <div className="px-6 pt-3 pb-2 shrink-0">
            <TabsList className="h-8 rounded-[2px] bg-muted/50 w-full grid grid-cols-3">
              <TabsTrigger value="all" className="text-xs rounded-[2px]">
                All
                <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px] rounded-[2px]">
                  {all.length}
                </Badge>
              </TabsTrigger>
              <TabsTrigger value="primitive" className="text-xs rounded-[2px]">
                <Cpu className="w-3 h-3 mr-1" />
                Primitive
                <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px] rounded-[2px]">
                  {primitives.length}
                </Badge>
              </TabsTrigger>
              <TabsTrigger value="ai-judge" className="text-xs rounded-[2px]">
                <Sparkles className="w-3 h-3 mr-1" />
                AI Judge
                <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px] rounded-[2px]">
                  {aiJudges.length}
                </Badge>
              </TabsTrigger>
            </TabsList>
          </div>

          {(["all", "primitive", "ai-judge"] as const).map((tab) => {
            const metrics = tab === "all" ? all : tab === "primitive" ? primitives : aiJudges
            return (
              <TabsContent key={tab} value={tab} className="flex-1 overflow-y-auto px-6 pb-6 mt-0 space-y-2">
                {metrics.length === 0 ? (
                  <div className="text-center py-10 text-sm text-muted-foreground">
                    {search ? "No metrics match your search." : "No metrics in this category."}
                  </div>
                ) : (
                  metrics.map((metric) => {
                    const isAdded = addedMetricIds.includes(metric.id)
                    return (
                      <MetricCard
                        key={metric.id}
                        metric={metric}
                        isAdded={isAdded}
                        onAdd={() => handleAdd(metric.name)}
                      />
                    )
                  })
                )}
              </TabsContent>
            )
          })}
        </Tabs>
      </SheetContent>
    </Sheet>
  )
}

function MetricCard({
  metric,
  isAdded,
  onAdd,
}: {
  metric: Metric
  isAdded: boolean
  onAdd: () => void
}) {
  const isAiJudge = metric.type === "ai-judge"

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-3 rounded-[2px] border transition-colors",
        isAdded
          ? "border-primary/20 bg-primary/5"
          : "border-border/40 bg-card/30 hover:border-border/60 hover:bg-card/60"
      )}
    >
      {/* Icon */}
      <div className={cn(
        "w-8 h-8 rounded-[2px] flex items-center justify-center shrink-0 mt-0.5",
        isAiJudge ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
      )}>
        {isAiJudge ? <Sparkles className="w-4 h-4" /> : <Cpu className="w-4 h-4" />}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium leading-none">{metric.name}</span>
          <Badge
            variant={isAiJudge ? "default" : "secondary"}
            className={cn(
              "text-[10px] font-mono rounded-[2px] px-1.5",
              isAiJudge ? "bg-primary/15 text-primary border-primary/20" : ""
            )}
          >
            {metric.type}
          </Badge>
        </div>
        {metric.description && (
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
            {metric.description}
          </p>
        )}
        {metric.scoring_scale && (
          <p className="text-[10px] font-mono text-muted-foreground/60">
            Score: {metric.scoring_scale.min} – {metric.scoring_scale.max} ({metric.scoring_scale.data_type})
          </p>
        )}
      </div>

      {/* Action */}
      <Button
        size="sm"
        variant={isAdded ? "ghost" : "outline"}
        className={cn(
          "h-7 w-7 rounded-[2px] shrink-0 p-0",
          isAdded
            ? "text-primary cursor-default"
            : "hover:border-primary/40 hover:bg-primary/10 hover:text-primary"
        )}
        onClick={isAdded ? undefined : onAdd}
        disabled={isAdded}
        title={isAdded ? "Already in pipeline" : `Add ${metric.name}`}
      >
        {isAdded ? (
          <Check className="w-3.5 h-3.5" />
        ) : (
          <Plus className="w-3.5 h-3.5" />
        )}
      </Button>
    </div>
  )
}
