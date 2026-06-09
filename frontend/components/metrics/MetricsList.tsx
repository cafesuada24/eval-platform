"use client"

import { useState, useMemo } from "react"
import { Search, ArrowUpDown, Check } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { Metric } from "@/lib/types"

type TypeFilter = "all" | "ai-judge" | "primitive"
type SortOption = "name-asc" | "name-desc" | "type-ai" | "type-primitive"

interface MetricsListProps {
  metrics: Metric[]
  selectedId: string | null
  onSelect: (id: string) => void
  className?: string
}

export function MetricsList({ metrics, selectedId, onSelect, className }: MetricsListProps) {
  const [query, setQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all")
  const [sortBy, setSortBy] = useState<SortOption>("name-asc")

  const filteredAndSorted = useMemo(() => {
    const q = query.toLowerCase()
    const filtered = metrics.filter((m) => {
      const matchesQuery =
        !q ||
        m.name.toLowerCase().includes(q) ||
        (m.description && m.description.toLowerCase().includes(q))
      const matchesType = typeFilter === "all" || m.type === typeFilter
      return matchesQuery && matchesType
    })

    return [...filtered].sort((a, b) => {
      switch (sortBy) {
        case "name-asc":
          return a.name.localeCompare(b.name)
        case "name-desc":
          return b.name.localeCompare(a.name)
        case "type-ai":
          if (a.type !== b.type) {
            return a.type === "ai-judge" ? -1 : 1
          }
          return a.name.localeCompare(b.name)
        case "type-primitive":
          if (a.type !== b.type) {
            return a.type === "primitive" ? -1 : 1
          }
          return a.name.localeCompare(b.name)
        default:
          return 0
      }
    })
  }, [metrics, query, typeFilter, sortBy])

  const aiJudgeCount = useMemo(
    () => metrics.filter((m) => m.type === "ai-judge").length,
    [metrics]
  )
  const primitiveCount = useMemo(
    () => metrics.filter((m) => m.type === "primitive").length,
    [metrics]
  )

  const tabs: { label: string; value: TypeFilter; count: number }[] = [
    { label: "All", value: "all", count: metrics.length },
    { label: "AI Judge", value: "ai-judge", count: aiJudgeCount },
    { label: "Primitive", value: "primitive", count: primitiveCount },
  ]

  return (
    <div className={cn("flex flex-col h-full border-r border-border/40", className)}>
      {/* Search + filter header */}
      <div className="p-3 space-y-2 shrink-0 border-b border-border/40 bg-card/20">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search metrics..."
              aria-label="Search metrics"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-8 h-8 text-xs rounded-[2px] bg-background"
            />
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8 rounded-[2px] border-border/40 bg-background hover:bg-muted/50 shrink-0"
                />
              }
            >
              <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onClick={() => setSortBy("name-asc")}
                className="flex items-center justify-between text-xs cursor-pointer"
              >
                <span>Name (A - Z)</span>
                {sortBy === "name-asc" && <Check className="h-3 w-3" />}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setSortBy("name-desc")}
                className="flex items-center justify-between text-xs cursor-pointer"
              >
                <span>Name (Z - A)</span>
                {sortBy === "name-desc" && <Check className="h-3 w-3" />}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setSortBy("type-ai")}
                className="flex items-center justify-between text-xs cursor-pointer"
              >
                <span>Type (AI Judge First)</span>
                {sortBy === "type-ai" && <Check className="h-3 w-3" />}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setSortBy("type-primitive")}
                className="flex items-center justify-between text-xs cursor-pointer"
              >
                <span>Type (Primitive First)</span>
                {sortBy === "type-primitive" && <Check className="h-3 w-3" />}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setTypeFilter(tab.value)}
              aria-pressed={typeFilter === tab.value}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-[2px] text-[10px] font-mono transition-colors",
                typeFilter === tab.value
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              {tab.label}
              <span
                className={cn(
                  "text-[9px] px-1 rounded-sm",
                  typeFilter === tab.value
                    ? "bg-primary/20 text-primary"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto" role="list" aria-label="Metrics">
        {filteredAndSorted.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-xs text-muted-foreground">
            No metrics match your search.
          </div>
        ) : (
          filteredAndSorted.map((metric) => {
            const isSelected = metric.id === selectedId
            const isAiJudge = metric.type === "ai-judge"
            return (
              <div key={metric.id} role="listitem">
                <button
                  onClick={() => onSelect(metric.id)}
                  aria-current={isSelected ? "true" : undefined}
                  className={cn(
                    "w-full text-left px-4 py-3 border-b border-border/30 transition-colors",
                    isSelected
                      ? "bg-primary/8 border-l-2 border-l-primary"
                      : "border-l-2 border-l-transparent hover:bg-muted/30"
                  )}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span
                      className={cn(
                        "text-xs font-semibold truncate",
                        isSelected ? "text-foreground" : "text-foreground/80"
                      )}
                      title={metric.name}
                    >
                      {metric.name}
                    </span>
                    <Badge
                      variant={isAiJudge ? "default" : "secondary"}
                      className={cn(
                        "text-[9px] rounded-[2px] font-mono shrink-0 px-1.5",
                        isAiJudge ? "bg-primary/10 text-primary border-primary/20" : ""
                      )}
                    >
                      {isAiJudge ? "AI JUDGE" : "PRIMITIVE"}
                    </Badge>
                  </div>
                  {metric.description && (
                    <p className="text-[10px] text-muted-foreground line-clamp-1 leading-relaxed">
                      {metric.description}
                    </p>
                  )}
                </button>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
