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

type Rule = {
  id: string
  type: "fail_over" | "fail_below" | "warning_over" | "warning_below"
  value: number
}

export function ThresholdBuilder() {
  const [rules, setRules] = useState<Rule[]>([])
  
  const addRule = () => {
    setRules([...rules, { id: Date.now().toString(), type: "fail_over", value: 0 }])
  }

  const updateRule = (id: string, updates: Partial<Rule>) => {
    setRules(rules.map(rule => rule.id === id ? { ...rule, ...updates } : rule))
  }

  const removeRule = (id: string) => {
    setRules(rules.filter(rule => rule.id !== id))
  }

  const getStyleForType = (type: Rule["type"]) => {
    if (type.includes("fail")) return "border-destructive/50 bg-destructive/10 text-destructive focus-within:border-destructive"
    if (type.includes("warning")) return "border-amber-500/50 bg-amber-500/10 text-amber-500 focus-within:border-amber-500"
    return "border-border"
  }

  return (
    <div className="space-y-4">
      {rules.length > 0 && (
        <div className="space-y-3">
          {rules.map((rule) => (
            <div key={rule.id} className="flex items-center gap-3">
              <div className={cn("flex items-center gap-2 p-1 border rounded-lg flex-1 transition-colors", getStyleForType(rule.type))}>
                <Select
                  value={rule.type}
                  onValueChange={(val: any) => updateRule(rule.id, { type: val })}
                >
                  <SelectTrigger className="border-0 shadow-none bg-transparent focus:ring-0 w-[160px]">
                    <SelectValue placeholder="Condition" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fail_over" className="text-destructive">Fail Over</SelectItem>
                    <SelectItem value="fail_below" className="text-destructive">Fail Below</SelectItem>
                    <SelectItem value="warning_over" className="text-amber-500">Warning Over</SelectItem>
                    <SelectItem value="warning_below" className="text-amber-500">Warning Below</SelectItem>
                  </SelectContent>
                </Select>
                <div className="h-4 w-px bg-current/20" />
                <Input
                  type="number"
                  value={rule.value}
                  onChange={(e) => updateRule(rule.id, { value: parseFloat(e.target.value) || 0 })}
                  className="border-0 shadow-none bg-transparent focus-visible:ring-0 px-2 font-mono"
                  placeholder="0.0"
                  step="0.1"
                />
              </div>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={() => removeRule(rule.id)}
                className="text-muted-foreground hover:text-destructive shrink-0"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
      <Button 
        variant="outline" 
        size="sm" 
        onClick={addRule}
        className="w-full border-dashed hover:bg-primary/5 hover:text-primary hover:border-primary/50 transition-colors"
      >
        <Plus className="w-4 h-4 mr-2" />
        Add Threshold Rule
      </Button>
    </div>
  )
}
