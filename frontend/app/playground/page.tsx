/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"
// @ts-nocheck

import { useState, useEffect, useRef } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { AgentChat } from "@/components/playground/AgentChat"
import { MetricConfigurator } from "@/components/playground/MetricConfigurator"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Save } from "lucide-react"

export const metricSchema = z.object({
  name: z.string().min(1, "Name is required"),
  prompt_template: z.string().min(10, "Prompt is too short"),
  data_type: z.enum(["integer", "float", "boolean"]),
  min_score: z.number(),
  max_score: z.number(),
  required_inputs: z.array(z.string()),
  provider: z.string(),
  model_name: z.string(),
  temperature: z.number().min(0).max(1)
}).refine((data) => data.min_score < data.max_score, {
  message: "Min score must be less than max score",
  path: ["min_score"]
});

export type MetricConfig = z.infer<typeof metricSchema>

import { useSearchParams } from "next/navigation"
import { Suspense } from "react"
import { ChatMessage } from "@/lib/types"

function PlaygroundContent() {
  const searchParams = useSearchParams();
  const initialMetricName = searchParams.get('metric');

  const [metricsList, setMetricsList] = useState<any[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<string>(initialMetricName || "new");
  
  // Hook states declared at the top to avoid temporal dead zone in callbacks
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const loadedSessionForRef = useRef<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm<MetricConfig>({
    resolver: zodResolver(metricSchema),
    defaultValues: {
      name: "",
      prompt_template: "",
      data_type: undefined,
      min_score: undefined as unknown as number,
      max_score: undefined as unknown as number,
      required_inputs: [],
      provider: undefined,
      model_name: "",
      temperature: 0.2
    }
  })

  // Fetch metrics list on mount
  useEffect(() => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${baseUrl}/v1/configs/metrics`)
      .then(res => res.json())
      .then(data => setMetricsList(data.filter((m: any) => m.type === 'ai-judge')))
      .catch(console.error);
  }, []);

  // Reload session messages from backend history
  const reloadSession = () => {
    if (selectedMetric === "new") {
      setMessages([]);
      return;
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const existingMetric = metricsList.find((m: any) => m.name === selectedMetric);
    fetch(`${baseUrl}/v1/agent/sessions/${existingMetric?.id || selectedMetric}`)
      .then(res => {
        if (res.ok) return res.json();
        throw new Error("Failed to load session");
      })
      .then(data => {
        if (data && data.messages) {
          // Avoid impure Math.random inside render cycles - generate deterministic ID
          setMessages(data.messages.map((msg: any, idx: number) => ({
            id: `msg-${Date.now()}-${idx}`,
            role: msg.role,
            content: msg.content
          })));
        } else {
          setMessages([]);
        }
      })
      .catch(err => {
        console.error("No persistent session found or error:", err);
        setMessages([]);
      });
  };

  // Submit feedback programmatically to the agent API
  const submitFeedback = async (feedbackText: string) => {
    if (!feedbackText.trim() || isLoading) return;
    
    // Pure ID generation using timestamp and simple index
    const userMessage: ChatMessage = { id: `msg-${Date.now()}-user`, role: 'user' as const, content: feedbackText };
    const currentMessages = [...messages, userMessage];
    setMessages(currentMessages);
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: currentMessages,
          metric_id: selectedMetric === "new" ? null : (metricsList.find((m: any) => m.name === selectedMetric)?.id || null),
          data: { current_yaml_config: JSON.stringify(form.getValues(), null, 2) }
        })
      });
      
      if (!response.ok) throw new Error("Failed to communicate with agent");
      
      const result = await response.json();
      
      if (result.metric_draft) {
        const m = result.metric_draft;
        if (m.name !== undefined) form.setValue('name', m.name, { shouldValidate: true, shouldDirty: true });
        if (m.prompt_template !== undefined) form.setValue('prompt_template', m.prompt_template, { shouldValidate: true, shouldDirty: true });
        if (m.required_inputs !== undefined) form.setValue('required_inputs', m.required_inputs, { shouldValidate: true, shouldDirty: true });
        
        if (m.model_provider !== undefined) form.setValue('provider', m.model_provider, { shouldValidate: true, shouldDirty: true });
        if (m.model_name !== undefined) form.setValue('model_name', m.model_name, { shouldValidate: true, shouldDirty: true });
        if (m.model_temperature !== undefined) form.setValue('temperature', m.model_temperature, { shouldValidate: true, shouldDirty: true });
        
        if (m.scoring_scale_min !== undefined) form.setValue('min_score', m.scoring_scale_min, { shouldValidate: true, shouldDirty: true });
        if (m.scoring_scale_max !== undefined) form.setValue('max_score', m.scoring_scale_max, { shouldValidate: true, shouldDirty: true });
        if (m.scoring_scale_type !== undefined) form.setValue('data_type', m.scoring_scale_type, { shouldValidate: true, shouldDirty: true });
        
        toast.success("Agent updated the configuration panel");
      }
      
      if (result.response_text) {
        setMessages(prev => [...prev, {
           id: `msg-${Date.now()}-agent`,
           role: 'model',
           content: result.response_text,
           runtime_id: result.runtime_id,
           toolInvocations: result.metric_draft ? [{ toolCallId: `call-${Date.now()}`, toolName: 'UpdateMetricConfigTool', result: 'success' }] : []
        }]);
      }
    } catch (_err) {
      toast.error("Agent failed to respond.");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle metric selection change
  useEffect(() => {
    if (selectedMetric === "new") {
      form.reset({
        name: "",
        prompt_template: "",
        data_type: undefined,
        min_score: undefined as unknown as number,
        max_score: undefined as unknown as number,
        required_inputs: [],
        provider: undefined,
        model_name: "",
        temperature: 0.2
      });
      // Defer state update to avoid synchronous setState inside render warnings
      setTimeout(() => {
        setMessages([]);
      }, 0);
      loadedSessionForRef.current = "new";
      return;
    }

    if (metricsList.length === 0) return;
    
    // Prevent fetching session and resetting form if we already loaded it for the active metric
    // This stops "Save" (which updates metricsList) from wiping out the active chat session
    if (loadedSessionForRef.current === selectedMetric) return;

    const m = metricsList.find((x: any) => x.name === selectedMetric);
    if (m) {
      if (m.name !== undefined) form.setValue('name', m.name);
      if (m.prompt_template !== undefined) form.setValue('prompt_template', m.prompt_template);
      if (m.required_inputs !== undefined) form.setValue('required_inputs', m.required_inputs);
      if (m.model_configuration) {
        if (m.model_configuration.provider !== undefined) form.setValue('provider', m.model_configuration.provider);
        if (m.model_configuration.model !== undefined) form.setValue('model_name', m.model_configuration.model);
        if (m.model_configuration.temperature !== undefined) form.setValue('temperature', m.model_configuration.temperature);
      }
      if (m.scoring_scale) {
        if (m.scoring_scale.min !== undefined) form.setValue('min_score', m.scoring_scale.min);
        if (m.scoring_scale.max !== undefined) form.setValue('max_score', m.scoring_scale.max);
        if (m.scoring_scale.data_type !== undefined) form.setValue('data_type', m.scoring_scale.data_type);
      }
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const existingMetric = metricsList.find((m: any) => m.name === selectedMetric);
    fetch(`${baseUrl}/v1/agent/sessions/${existingMetric?.id || selectedMetric}`)
      .then(res => {
        if (res.ok) return res.json();
        throw new Error("Failed to load session");
      })
      .then(data => {
        if (data && data.messages) {
          setMessages(data.messages.map((msg: any, idx: number) => ({
            id: `msg-${Date.now()}-${idx}`,
            role: msg.role,
            content: msg.content,
            runtime_id: msg.runtime_id
          })));
        } else {
          setMessages([]);
        }
      })
      .catch(_err => {
        setMessages([]);
      })
      .finally(() => {
        loadedSessionForRef.current = selectedMetric;
      });
  }, [selectedMetric, metricsList, form]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => setInput(e.target.value)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    const userMessage: ChatMessage = { id: `msg-${Date.now()}-user`, role: 'user' as const, content: input };
    const currentMessages = [...messages, userMessage];
    setMessages(currentMessages);
    setInput("");
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: currentMessages,
          metric_id: selectedMetric === "new" ? null : (metricsList.find((m: any) => m.name === selectedMetric)?.id || null),
          data: { current_yaml_config: JSON.stringify(form.getValues(), null, 2) }
        })
      });
      
      if (!response.ok) throw new Error("Failed to communicate with agent");
      
      const result = await response.json();
      
      if (result.metric_draft) {
        const m = result.metric_draft;
        if (m.name !== undefined) form.setValue('name', m.name, { shouldValidate: true, shouldDirty: true });
        if (m.prompt_template !== undefined) form.setValue('prompt_template', m.prompt_template, { shouldValidate: true, shouldDirty: true });
        if (m.required_inputs !== undefined) form.setValue('required_inputs', m.required_inputs, { shouldValidate: true, shouldDirty: true });
        
        if (m.model_provider !== undefined) form.setValue('provider', m.model_provider, { shouldValidate: true, shouldDirty: true });
        if (m.model_name !== undefined) form.setValue('model_name', m.model_name, { shouldValidate: true, shouldDirty: true });
        if (m.model_temperature !== undefined) form.setValue('temperature', m.model_temperature, { shouldValidate: true, shouldDirty: true });
        
        if (m.scoring_scale_min !== undefined) form.setValue('min_score', m.scoring_scale_min, { shouldValidate: true, shouldDirty: true });
        if (m.scoring_scale_max !== undefined) form.setValue('max_score', m.scoring_scale_max, { shouldValidate: true, shouldDirty: true });
        if (m.scoring_scale_type !== undefined) form.setValue('data_type', m.scoring_scale_type, { shouldValidate: true, shouldDirty: true });
        
        toast.success("Agent updated the configuration panel");
      }
      
      if (result.response_text) {
        setMessages(prev => [...prev, {
           id: `msg-${Date.now()}-agent`,
           role: 'model',
           content: result.response_text,
           runtime_id: result.runtime_id,
           toolInvocations: result.metric_draft ? [{ toolCallId: `call-${Date.now()}`, toolName: 'UpdateMetricConfigTool', result: 'success' }] : []
        }]);
      }
    } catch (_err) {
      toast.error("Agent failed to respond.");
    } finally {
      setIsLoading(false);
    }
  }

  const handleSave = form.handleSubmit(async (data) => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const isNew = selectedMetric === "new";
      const existingMetric = isNew ? null : metricsList.find((m: any) => m.name === selectedMetric);
      
      const payload: any = {
        name: data.name,
        type: "ai-judge",
        description: `Custom AI judge metric for ${data.name}`,
        required_inputs: data.required_inputs,
        prompt_template: data.prompt_template,
        model_configuration: {
          provider: data.provider,
          model: data.model_name,
          temperature: data.temperature
        },
        scoring_scale: {
          min: data.min_score,
          max: data.max_score,
          data_type: data.data_type
        }
      };

      if (!isNew && existingMetric?.id) {
        payload.id = existingMetric.id;
      }

      const url = isNew 
        ? `${baseUrl}/v1/configs/metrics` 
        : `${baseUrl}/v1/configs/metrics/${existingMetric?.id || data.name}`;
      
      const res = await fetch(url, {
        method: isNew ? 'POST' : 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        throw new Error("Failed to save metric");
      }
      
      const savedMetric = await res.json();
      
      // Explicitly save the agent chat session against this metric
      if (messages.length > 0) {
        const sanitizedMessages = messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          runtime_id: msg.runtime_id
        }));
        const targetId = savedMetric?.id || existingMetric?.id || data.name;
        await fetch(`${baseUrl}/v1/agent/sessions/${targetId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: sanitizedMessages })
        }).catch(err => console.error("Failed to persist agent session:", err));
      }

      toast.success("Metric configuration saved successfully.");
      
      // Refresh metrics list after save
      fetch(`${baseUrl}/v1/configs/metrics`)
        .then(r => r.json())
        .then(d => {
          setMetricsList(d.filter((m: any) => m.type === 'ai-judge'));
          if (selectedMetric !== data.name) {
            setSelectedMetric(data.name);
          }
        })
        .catch(console.error);

    } catch (_err) {
      toast.error("Failed to save metric configuration to API.");
    }
  }, (errors) => {
    if (errors.min_score) {
      toast.error(errors.min_score.message || "Validation Error")
    } else {
      toast.error("Please fix the validation errors before saving.")
    }
  });

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/50 bg-background shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold tracking-tight">Metric Playground</h1>
          <div className="flex items-center gap-2">
            <span className={`flex h-2 w-2 rounded-full ${isLoading ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500 animate-pulse'}`} />
            <span className="text-xs text-muted-foreground font-medium">
              {isLoading ? 'Agent Thinking...' : 'Agent Connected'}
            </span>
          </div>
        </div>
        <Button size="sm" onClick={handleSave} className="h-8">
          <Save className="w-4 h-4 mr-2" />
          Save Metric
        </Button>
      </div>

      <ResizablePanelGroup orientation="horizontal" className="flex-1 overflow-hidden">
        <ResizablePanel defaultSize={40} minSize={25} className="flex flex-col h-full bg-background relative">
          <AgentChat 
            messages={messages} 
            setMessages={setMessages}
            input={input} 
            setInput={setInput}
            handleInputChange={handleInputChange} 
            handleSubmit={handleSubmit}
            isLoading={isLoading}
            form={form}
            selectedMetric={selectedMetric}
            selectedMetricId={selectedMetric === "new" ? null : (metricsList.find((m: any) => m.name === selectedMetric)?.id || null)}
            reloadSession={reloadSession}
            submitFeedback={submitFeedback}
          />
        </ResizablePanel>
        
        <ResizableHandle className="w-1.5 bg-border/50 hover:bg-primary/50 transition-colors data-[resize-handle-state=drag]:bg-primary" />
        
        <ResizablePanel defaultSize={60} minSize={30} className="flex flex-col h-full bg-card/30">
          <MetricConfigurator 
            form={form} 
            metricsList={metricsList}
            selectedMetric={selectedMetric}
            onSelectMetric={setSelectedMetric}
          />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}

export default function PlaygroundPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PlaygroundContent />
    </Suspense>
  )
}
