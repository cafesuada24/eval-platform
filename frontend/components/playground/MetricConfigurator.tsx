"use client"

import { Info, CheckCircle2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"

const systemExtractors = ["output_text", "user_prompt", "context_documents"]

export function MetricConfigurator() {
  const requiredInputs = ["output_text", "custom_guidelines"]

  return (
    <div className="flex flex-col h-full bg-card/30 overflow-hidden">
      <Tabs defaultValue="prompt" className="flex flex-col h-full w-full">
        <div className="px-6 pt-4 pb-2 border-b border-border/50">
          <TabsList className="grid w-full grid-cols-2 bg-muted/50">
            <TabsTrigger value="prompt">Prompt Definition</TabsTrigger>
            <TabsTrigger value="model">Model Config</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="prompt" className="flex-1 overflow-y-auto p-6 space-y-6 mt-0">
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Metric Name</label>
              <Input defaultValue="Relevance Scorer" className="bg-background/50 font-medium" />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Prompt Template</label>
                <Badge variant="outline" className="text-xs font-mono">system</Badge>
              </div>
              <Textarea 
                className="min-h-[200px] font-mono text-sm bg-background/50 resize-none" 
                defaultValue={`You are an expert AI judge. Evaluate the {{output_text}} against the {{custom_guidelines}}...`}
              />
              <div className="flex items-start gap-2 p-3 bg-primary/5 border border-primary/20 rounded-lg text-xs text-muted-foreground mt-2">
                <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                <p>
                  System automatically appends strict JSON formatting instructions at runtime. Do not add JSON rules manually.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Data Type</label>
                <Select defaultValue="integer">
                  <SelectTrigger className="bg-background/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="integer">Integer</SelectItem>
                    <SelectItem value="float">Float</SelectItem>
                    <SelectItem value="boolean">Boolean</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">Min</label>
                  <Input type="number" defaultValue="1" className="bg-background/50" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">Max</label>
                  <Input type="number" defaultValue="5" className="bg-background/50" />
                </div>
              </div>
            </div>

            <div className="space-y-3 pt-4 border-t border-border/50">
              <label className="text-sm font-medium">Required Extractors (Input Variables)</label>
              <div className="flex flex-col gap-2">
                {requiredInputs.map(input => {
                  const isAutoBound = systemExtractors.includes(input)
                  return (
                    <div key={input} className="flex items-center justify-between p-2 rounded-md bg-background/50 border border-border/50">
                      <span className="font-mono text-sm">{input}</span>
                      {isAutoBound ? (
                        <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:bg-emerald-500/20 gap-1.5 font-normal">
                          <CheckCircle2 className="w-3 h-3" />
                          Auto-bound
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-muted-foreground gap-1.5 font-normal">
                          Requires Pipeline Mapping
                        </Badge>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="model" className="flex-1 overflow-y-auto p-6 space-y-6 mt-0">
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">AI Provider</label>
              <Select defaultValue="google">
                <SelectTrigger className="bg-background/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="google">Google Gemini</SelectItem>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="anthropic">Anthropic</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Model Name</label>
              <Input defaultValue="gemini-2.5-pro" className="bg-background/50 font-mono text-sm" />
            </div>

            <div className="space-y-4 pt-4 border-t border-border/50">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Temperature</label>
                <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">0.2</span>
              </div>
              <Slider 
                defaultValue={[0.2]} 
                max={1} 
                step={0.1}
                className="py-4"
              />
              <p className="text-xs text-muted-foreground">
                Lower temperature increases deterministic output. Recommended for evaluation metrics.
              </p>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
