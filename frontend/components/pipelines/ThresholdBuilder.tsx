"use client"

import { useState } from "react"
import { Plus, X } from "lucide-react"
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

export function ThresholdBuilder({ value = {}, onChange, scoringScale }: Props) {
  const [rules, setRules] = useState<Rule[]>(() => {
    return Object.entries(value || {})
      .filter(([_, val]) => val !== null && val !== undefined)
      .map(([key, val], i) => ({
        id: `${key}-${i}`,
        type: key as Rule["type"],
        value: val as number,
      }));
  });
  
  const notifyChange = (newRules: Rule[]) => {
    setRules(newRules);
    
    if (!onChange) return;
    const newThresholds: any = {};
    newRules.forEach(r => {
      const parsed = typeof r.value === 'string' ? parseFloat(r.value) : r.value;
      if (typeof parsed === 'number' && !isNaN(parsed)) {
        newThresholds[r.type] = parsed;
      }
    });
    onChange(newThresholds);
  };

  const usedTypes = rules.map(r => r.type);
  const availableTypes = (["fail_over", "fail_below", "warning_over", "warning_below"] as const)
    .filter(t => !usedTypes.includes(t));

  const addRule = () => {
    if (availableTypes.length === 0) return;
    notifyChange([...rules, { id: Date.now().toString(), type: availableTypes[0], value: "" }])
  }

  const updateRule = (id: string, updates: Partial<Rule>) => {
    notifyChange(rules.map(rule => rule.id === id ? { ...rule, ...updates } : rule))
  }

  const removeRule = (id: string) => {
    notifyChange(rules.filter(rule => rule.id !== id))
  }

  const getStyleForType = (type: Rule["type"]) => {
    if (type.includes("fail")) return "border-l-destructive focus-within:ring-destructive/20 bg-destructive/5"
    if (type.includes("warning")) return "border-l-amber-500 focus-within:ring-amber-500/20 bg-amber-500/5"
    return "border-l-border focus-within:ring-border/20 bg-card/50"
  }

  const validateRule = (rule: Rule) => {
    const parsed = typeof rule.value === 'string' ? parseFloat(rule.value) : rule.value;
    if (isNaN(parsed)) return true; // Empty string is fine, it just won't save
    if (!scoringScale) return true;
    if (parsed < scoringScale.min || parsed > scoringScale.max) return false;
    if (scoringScale.data_type === "integer" && !Number.isInteger(parsed)) return false;
    return true;
  }

  const step = scoringScale?.data_type === "integer" ? "1" : "0.1";
  const placeholder = scoringScale ? `${scoringScale.min}${scoringScale.data_type === 'float' ? '.0' : ''}` : "0.0";

  return (
    <div className="space-y-4">
      {rules.length > 0 && (
        <div className="space-y-2">
          {rules.map((rule) => {
            const isValid = validateRule(rule);
            return (
            <div key={rule.id} className="flex items-center gap-2 group">
              <div className={cn(
                "flex items-center gap-2 py-0.5 px-1 border rounded-[2px] flex-1 transition-all shadow-sm border-l-4 focus-within:ring-2", 
                getStyleForType(rule.type),
                !isValid && "border-destructive/50 ring-1 ring-destructive/50"
              )}>
                <Select
                  value={rule.type}
                  onValueChange={(val: any) => updateRule(rule.id, { type: val })}
                >
                  <SelectTrigger className="border-0 shadow-none bg-transparent focus:ring-0 w-[140px] h-8 text-sm font-medium rounded-[2px]">
                    <SelectValue placeholder="Condition" />
                  </SelectTrigger>
                  <SelectContent className="rounded-[2px]">
                    <SelectItem value="fail_over" className="text-destructive font-medium" disabled={rule.type !== "fail_over" && usedTypes.includes("fail_over")}>Fail Over</SelectItem>
                    <SelectItem value="fail_below" className="text-destructive font-medium" disabled={rule.type !== "fail_below" && usedTypes.includes("fail_below")}>Fail Below</SelectItem>
                    <SelectItem value="warning_over" className="text-amber-500 font-medium" disabled={rule.type !== "warning_over" && usedTypes.includes("warning_over")}>Warning Over</SelectItem>
                    <SelectItem value="warning_below" className="text-amber-500 font-medium" disabled={rule.type !== "warning_below" && usedTypes.includes("warning_below")}>Warning Below</SelectItem>
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
          )})}
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
  )
}
