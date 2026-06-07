"use client"

import { useState, useEffect } from "react"
import { Plus, X, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { Metric } from "@/lib/types"

type Rule = {
  id: string
  type: "fail_over" | "fail_below" | "warning_over" | "warning_below"
  value: string | number
}

export type Thresholds = {
  fail_over?: number;
  fail_below?: number;
  warning_over?: number;
  warning_below?: number;
}

interface Props {
  value?: Thresholds;
  onChange?: (thresholds: Thresholds) => void;
  scoringScale?: Metric["scoring_scale"];
}

/** Colour-banded range bar visualising pass / warn / fail zones */
function ThresholdRangeBar({
  thresholds,
  scoringScale,
}: {
  thresholds: Thresholds
  scoringScale: Metric["scoring_scale"]
}) {
  const { min, max } = scoringScale
  const range = max - min
  if (range <= 0) return null

  const toPercent = (v: number) => Math.max(0, Math.min(100, ((v - min) / range) * 100))

  const { fail_below, fail_over, warning_below, warning_over } = thresholds
  const hasAny = fail_below !== undefined || fail_over !== undefined || warning_below !== undefined || warning_over !== undefined

  type Seg = { start: number; end: number; color: string }
  const segments: Seg[] = []

  const push = (start: number, end: number, color: string) => {
    if (end > start) segments.push({ start, end, color })
  }

  if (!hasAny) {
    push(min, max, "bg-muted/50")
  } else {
    let cursor = min

    if (fail_below !== undefined && fail_below > cursor) {
      push(cursor, fail_below, "bg-destructive/60")
      cursor = fail_below
    }
    if (warning_below !== undefined && warning_below > cursor) {
      push(cursor, warning_below, "bg-amber-500/60")
      cursor = warning_below
    }
    const passEnd =
      warning_over !== undefined
        ? warning_over
        : fail_over !== undefined
        ? fail_over
        : max
    if (passEnd > cursor) {
      push(cursor, passEnd, "bg-emerald-500/60")
      cursor = passEnd
    }
    if (warning_over !== undefined && fail_over !== undefined && fail_over > warning_over && warning_over > cursor) {
      push(cursor, fail_over, "bg-amber-500/60")
      cursor = fail_over
    } else if (warning_over !== undefined && warning_over > cursor) {
      push(cursor, warning_over > max ? max : warning_over, "bg-amber-500/60")
      cursor = warning_over
    }
    if (fail_over !== undefined && fail_over > cursor) {
      push(cursor, fail_over > max ? max : fail_over, "bg-amber-500/60")
      cursor = fail_over
    }
    if (cursor < max) {
      push(cursor, max, fail_over !== undefined ? "bg-destructive/60" : "bg-muted/50")
    }
  }

  const markers: Array<{ pct: number; color: string; label: string }> = []
  if (fail_below !== undefined) markers.push({ pct: toPercent(fail_below), color: "text-destructive", label: String(fail_below) })
  if (warning_below !== undefined) markers.push({ pct: toPercent(warning_below), color: "text-amber-500", label: String(warning_below) })
  if (warning_over !== undefined) markers.push({ pct: toPercent(warning_over), color: "text-amber-500", label: String(warning_over) })
  if (fail_over !== undefined) markers.push({ pct: toPercent(fail_over), color: "text-destructive", label: String(fail_over) })

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-[10px] font-mono text-muted-foreground/40 select-none">
        <span>{min}</span>
        <span>{max}</span>
      </div>
      <div className="relative h-3 rounded-full overflow-hidden bg-muted/20 border border-border/20">
        {segments.map((seg, i) => (
          <div
            key={i}
            className={cn("absolute top-0 bottom-0 transition-all", seg.color)}
            style={{
              left: `${toPercent(seg.start)}%`,
              width: `${toPercent(seg.end) - toPercent(seg.start)}%`,
            }}
          />
        ))}
        {markers.map((m, i) => (
          <div
            key={i}
            className="absolute top-0 bottom-0 w-px bg-background/70"
            style={{ left: `${m.pct}%` }}
          />
        ))}
      </div>
      {markers.length > 0 && (
        <div className="relative h-4 select-none">
          {markers.map((m, i) => (
            <span
              key={i}
              className={cn("absolute -translate-x-1/2 text-[9px] font-mono font-semibold", m.color)}
              style={{ left: `${m.pct}%` }}
            >
              {m.label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function valuesToRules(thresholds: Thresholds): Rule[] {
  return Object.entries(thresholds || {})
    .filter(([, val]) => val !== null && val !== undefined)
    .map(([key, val], i) => ({
      id: `${key}-${i}`,
      type: key as Rule["type"],
      value: val as number,
    }));
}

export function ThresholdBuilder({ value = {}, onChange, scoringScale }: Props) {
  const [rules, setRules] = useState<Rule[]>(() => valuesToRules(value))
  const [expanded, setExpanded] = useState(rules.length > 0)

  // Sync rules when the parent passes a new value (e.g. metric switch).
  // The dependency is stringified to avoid object-reference churn.
  const valueStr = JSON.stringify(value);
  useEffect(() => {
    const next = valuesToRules(JSON.parse(valueStr) as Thresholds);
    // Adjusting derived local state when a prop changes is the documented exception:
    // react.dev/learn/you-might-not-need-an-effect §"Adjusting some state when a prop changes"
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRules(next);
    setExpanded(next.length > 0);
  }, [valueStr]);

  const notifyChange = (newRules: Rule[]) => {
    setRules(newRules)
    if (!onChange) return
    const next: Thresholds = {}
    newRules.forEach((r) => {
      const parsed = typeof r.value === "string" ? parseFloat(r.value) : r.value
      if (typeof parsed === "number" && !isNaN(parsed)) {
        next[r.type] = parsed
      }
    })
    onChange(next)
  }

  const usedTypes = rules.map((r) => r.type)
  const availableTypes = (
    ["fail_over", "fail_below", "warning_over", "warning_below"] as const
  ).filter((t) => !usedTypes.includes(t))

  const addRule = () => {
    if (availableTypes.length === 0) return
    setExpanded(true)
    notifyChange([...rules, { id: Date.now().toString(), type: availableTypes[0], value: "" }])
  }

  const updateRule = (id: string, updates: Partial<Rule>) =>
    notifyChange(rules.map((r) => (r.id === id ? { ...r, ...updates } : r)))

  const removeRule = (id: string) =>
    notifyChange(rules.filter((r) => r.id !== id))

  const getStyleForType = (type: Rule["type"]) => {
    if (type.includes("fail")) return "border-l-destructive focus-within:ring-destructive/20 bg-destructive/5"
    if (type.includes("warning")) return "border-l-amber-500 focus-within:ring-amber-500/20 bg-amber-500/5"
    return "border-l-border focus-within:ring-border/20 bg-card/50"
  }

  const validateRule = (rule: Rule) => {
    const parsed = typeof rule.value === "string" ? parseFloat(rule.value) : rule.value
    if (isNaN(parsed)) return true
    if (!scoringScale) return true
    if (parsed < scoringScale.min || parsed > scoringScale.max) return false
    if (scoringScale.data_type === "integer" && !Number.isInteger(parsed)) return false
    return true
  }

  const step = scoringScale?.data_type === "integer" ? "1" : "0.1"
  const placeholder = scoringScale
    ? `${scoringScale.min}${scoringScale.data_type === "float" ? ".0" : ""}`
    : "0.0"

  // Build current thresholds for the visual bar
  const currentThresholds: Thresholds = {}
  rules.forEach((r) => {
    const parsed = typeof r.value === "string" ? parseFloat(r.value) : r.value
    if (typeof parsed === "number" && !isNaN(parsed)) {
      currentThresholds[r.type] = parsed
    }
  })

  return (
    <div className="space-y-3">
      {/* Visual range bar */}
      {scoringScale && (
        <ThresholdRangeBar thresholds={currentThresholds} scoringScale={scoringScale} />
      )}

      {/* Collapsible rule editor */}
      <div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-2"
        >
          <ChevronDown
            className={cn("w-3 h-3 transition-transform", expanded ? "rotate-0" : "-rotate-90")}
          />
          <span>
            {rules.length === 0
              ? "Set threshold rules"
              : `${rules.length} rule${rules.length !== 1 ? "s" : ""} configured`}
          </span>
        </button>

        {expanded && (
          <div className="space-y-4">
            {rules.length > 0 && (
              <div className="space-y-2">
                {rules.map((rule) => {
                  const isValid = validateRule(rule)
                  return (
                    <div key={rule.id} className="flex items-center gap-2 group">
                      <div
                        className={cn(
                          "flex items-center gap-2 py-0.5 px-1 border rounded-[2px] flex-1 transition-all shadow-sm border-l-4 focus-within:ring-2",
                          getStyleForType(rule.type),
                          !isValid && "border-destructive/50 ring-1 ring-destructive/50"
                        )}
                      >
                        <Select
                          value={rule.type}
                          onValueChange={(val) => { if (val) updateRule(rule.id, { type: val as Rule["type"] }); }}
                        >
                          <SelectTrigger className="border-0 shadow-none bg-transparent focus:ring-0 w-[140px] h-8 text-sm font-medium rounded-[2px]">
                            <SelectValue placeholder="Condition" />
                          </SelectTrigger>
                          <SelectContent className="rounded-[2px]">
                            <SelectItem
                              value="fail_over"
                              className="text-destructive font-medium"
                              disabled={rule.type !== "fail_over" && usedTypes.includes("fail_over")}
                            >
                              Fail Over
                            </SelectItem>
                            <SelectItem
                              value="fail_below"
                              className="text-destructive font-medium"
                              disabled={rule.type !== "fail_below" && usedTypes.includes("fail_below")}
                            >
                              Fail Below
                            </SelectItem>
                            <SelectItem
                              value="warning_over"
                              className="text-amber-500 font-medium"
                              disabled={rule.type !== "warning_over" && usedTypes.includes("warning_over")}
                            >
                              Warning Over
                            </SelectItem>
                            <SelectItem
                              value="warning_below"
                              className="text-amber-500 font-medium"
                              disabled={rule.type !== "warning_below" && usedTypes.includes("warning_below")}
                            >
                              Warning Below
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <div className="h-4 w-px bg-border/50" />
                        <Input
                          type="number"
                          value={rule.value}
                          onChange={(e) => updateRule(rule.id, { value: e.target.value })}
                          className={cn(
                            "border-0 shadow-none bg-transparent focus-visible:ring-0 px-2 font-mono text-right h-8 rounded-[2px]",
                            !isValid && "text-destructive"
                          )}
                          placeholder={placeholder}
                          step={step}
                          min={scoringScale?.min}
                          max={scoringScale?.max}
                        />
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeRule(rule.id)}
                        className="text-muted-foreground hover:text-destructive shrink-0 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 rounded-[2px]"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={addRule}
              disabled={availableTypes.length === 0}
              className="w-full border-dashed bg-transparent hover:bg-card hover:text-primary hover:border-primary/50 transition-colors h-8 disabled:opacity-50 disabled:cursor-not-allowed rounded-[2px]"
            >
              <Plus className="w-3 h-3 mr-2" />
              Add Rule
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
