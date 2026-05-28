"use client"

import { Info, CheckCircle2, Plus, X } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { UseFormReturn, useFieldArray } from "react-hook-form"
import { MetricConfig } from "@/app/playground/page"
import { Button } from "@/components/ui/button"

const systemExtractors = ["output_text", "user_prompt", "context_documents"]

interface MetricConfiguratorProps {
  form: UseFormReturn<MetricConfig>
  metricsList: any[]
  selectedMetric: string
  onSelectMetric: (val: string) => void
}

export function MetricConfigurator({ form, metricsList, selectedMetric, onSelectMetric }: MetricConfiguratorProps) {
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "required_inputs" as never, // react-hook-form type workaround for string[]
  });

  // Since required_inputs is an array of strings, we handle it manually
  const requiredInputs = form.watch("required_inputs");

  const addRequiredInput = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && e.currentTarget.value.trim()) {
      e.preventDefault();
      const val = e.currentTarget.value.trim();
      if (!requiredInputs.includes(val)) {
        form.setValue("required_inputs", [...requiredInputs, val], { shouldDirty: true, shouldValidate: true });
      }
      e.currentTarget.value = "";
    }
  }

  const removeRequiredInput = (index: number) => {
    const newInputs = [...requiredInputs];
    newInputs.splice(index, 1);
    form.setValue("required_inputs", newInputs, { shouldDirty: true, shouldValidate: true });
  }

  return (
    <Form {...form}>
      <form className="flex flex-col h-full bg-card/30 overflow-hidden">
        <div className="px-6 py-3 flex items-center justify-between border-b border-border/50 bg-background/50 shrink-0">
          <h2 className="text-sm font-semibold tracking-tight text-muted-foreground">Active Metric</h2>
          <Select value={selectedMetric} onValueChange={(val) => val && onSelectMetric(val)}>
            <SelectTrigger className="w-[250px] bg-background">
              <SelectValue placeholder="Select a metric" />
            </SelectTrigger>
            <SelectContent className="max-h-[300px] overflow-y-auto">
              <SelectItem value="new">
                <div className="flex items-center text-primary font-medium">
                  <Plus className="w-4 h-4 mr-2" />
                  New Metric
                </div>
              </SelectItem>
              {metricsList.map((m: any) => (
                <SelectItem key={m.name} value={m.name}>{m.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Tabs defaultValue="prompt" className="flex flex-col h-full w-full">
          <div className="px-6 pt-4 pb-2 border-b border-border/50 shrink-0">
            <TabsList className="grid w-full grid-cols-2 bg-muted/50">
              <TabsTrigger value="prompt">Prompt Definition</TabsTrigger>
              <TabsTrigger value="model">Model Config</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="prompt" className="flex-1 overflow-y-auto p-6 space-y-6 mt-0">
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Metric Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Helpfulness Scorer" {...field} className="bg-background/50 font-medium" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="prompt_template"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex items-center justify-between">
                      <FormLabel>Prompt Template</FormLabel>
                      <Badge variant="outline" className="text-xs font-mono">system</Badge>
                    </div>
                    <FormControl>
                      <Textarea 
                        placeholder="e.g. You are an expert AI judge. Evaluate the {{output_text}}..."
                        {...field}
                        className="min-h-[200px] font-mono text-sm bg-background/50 resize-none" 
                      />
                    </FormControl>
                    <div className="flex items-start gap-2 p-3 bg-primary/5 border border-primary/20 rounded-lg text-xs text-muted-foreground mt-2">
                      <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                      <p>
                        System automatically appends strict JSON formatting instructions at runtime. Do not add JSON rules manually.
                      </p>
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="data_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Data Type</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value || ""}>
                        <FormControl>
                          <SelectTrigger className="bg-background/50">
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="integer">Integer</SelectItem>
                          <SelectItem value="float">Float</SelectItem>
                          <SelectItem value="boolean">Boolean</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="grid grid-cols-2 gap-2">
                  <FormField
                    control={form.control}
                    name="min_score"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-muted-foreground">Min</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="1"
                            type="number" 
                            {...field} 
                            value={field.value ?? ""}
                            onChange={e => field.onChange(parseFloat(e.target.value))} 
                            className="bg-background/50" 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="max_score"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-muted-foreground">Max</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="5"
                            type="number" 
                            {...field} 
                            value={field.value ?? ""}
                            onChange={e => field.onChange(parseFloat(e.target.value))} 
                            className="bg-background/50" 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              <div className="space-y-3 pt-4 border-t border-border/50">
                <label className="text-sm font-medium">Required Extractors (Input Variables)</label>
                <div className="flex flex-col gap-2">
                  {requiredInputs.map((input, index) => {
                    const isAutoBound = systemExtractors.includes(input)
                    return (
                      <div key={index} className="flex items-center justify-between p-2 rounded-md bg-background/50 border border-border/50 group">
                        <span className="font-mono text-sm">{input}</span>
                        <div className="flex items-center gap-2">
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
                          <Button 
                            type="button" 
                            variant="ghost" 
                            size="icon" 
                            className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                            onClick={() => removeRequiredInput(index)}
                          >
                            <X className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                  <Input 
                    placeholder="Type new variable and press Enter..." 
                    className="bg-background/30 border-dashed text-sm font-mono h-8"
                    onKeyDown={addRequiredInput}
                  />
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="model" className="flex-1 overflow-y-auto p-6 space-y-6 mt-0">
            <div className="space-y-6">
              <FormField
                control={form.control}
                name="provider"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>AI Provider</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value || ""}>
                      <FormControl>
                        <SelectTrigger className="bg-background/50">
                          <SelectValue placeholder="Select provider" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="google">Google Gemini</SelectItem>
                        <SelectItem value="openai">OpenAI</SelectItem>
                        <SelectItem value="anthropic">Anthropic</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="model_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Model Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. gemini-2.5-pro" {...field} className="bg-background/50 font-mono text-sm" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="temperature"
                render={({ field }) => (
                  <FormItem className="pt-4 border-t border-border/50">
                    <div className="flex items-center justify-between">
                      <FormLabel>Temperature</FormLabel>
                      <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {field.value}
                      </span>
                    </div>
                    <FormControl>
                      <Slider 
                        value={[field.value]}
                        max={1} 
                        step={0.1}
                        onValueChange={(vals) => field.onChange((vals as any)[0])}
                        className="py-4"
                      />
                    </FormControl>
                    <p className="text-xs text-muted-foreground">
                      Lower temperature increases deterministic output. Recommended for evaluation metrics.
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </TabsContent>
        </Tabs>
      </form>
    </Form>
  )
}
