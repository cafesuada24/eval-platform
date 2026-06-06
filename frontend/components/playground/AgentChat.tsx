/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
"use client"
// @ts-nocheck

import { useState, useEffect } from "react"
import { 
  Send, Bot, User, Sparkles, TestTube, MessageSquare, 
  HelpCircle, Loader2, Play, Upload, ChevronDown, ChevronUp, 
  Trash2, Eye, FileText, X
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "sonner"
import { UseFormReturn } from "react-hook-form"
import { MetricConfig } from "@/app/playground/page"
import { ChatMessage } from "@/lib/types"
import { RuntimeInspectorModal } from "./RuntimeInspectorModal"
import { FileManagerModal } from "./FileManagerModal"
import { FolderOpen } from "lucide-react"

interface AgentChatProps {
  messages: ChatMessage[]
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
  input: string
  setInput: React.Dispatch<React.SetStateAction<string>>
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void
  isLoading?: boolean
  form: UseFormReturn<MetricConfig>
  selectedMetric: string
  selectedMetricId?: string | null
  reloadSession?: () => void
  submitFeedback?: (feedbackText: string) => Promise<void>
}

interface UploadedArtifact {
  id: string
  name: string
  text: string
  size: number
}

// Collapsible Row for variable values to keep timeline clean and "reasonable"
const VariableValueRow = ({ name, value }: { name: string; value: string }) => {
  const [expanded, setExpanded] = useState(false);
  const isLong = value.length > 120;
  
  return (
    <div className="leading-relaxed border-b border-border/30 last:border-b-0 pb-2 last:pb-0 pt-2 first:pt-0">
      <span className="text-emerald-700 dark:text-emerald-400 font-bold font-mono text-[10px] uppercase tracking-wider block mb-1">{name}</span>
      <div className="relative">
        <p className={`text-foreground/90 font-mono text-[11px] whitespace-pre-wrap break-all leading-normal ${!expanded && isLong ? "max-h-[50px] overflow-hidden opacity-85" : ""}`}>
          {value}
        </p>
        {isLong && (
          <button 
            onClick={() => setExpanded(!expanded)} 
            className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold hover:underline block mt-1 shrink-0"
          >
            {expanded ? "Collapse Content ▲" : "View Entire Content (Long Document) ▼"}
          </button>
        )}
      </div>
    </div>
  );
};

const getMessageContent = (msg: any) => {
  if (msg.content) return msg.content;
  if (msg.parts && Array.isArray(msg.parts)) {
    return msg.parts.map((p: any) => p.text || '').join('');
  }
  return '';
};



export function AgentChat({ 
  messages, 
  setMessages,
  input, 
  setInput,
  handleInputChange, 
  handleSubmit, 
  isLoading,
  form,
  selectedMetric,
  selectedMetricId,
  reloadSession,
  submitFeedback
}: AgentChatProps) {
  // Required inputs from the active form state
  const requiredInputs = form.watch("required_inputs") || [];

  const [selectedRuntimeId, setSelectedRuntimeId] = useState<string | null>(null);
  const [isFileManagerOpen, setIsFileManagerOpen] = useState(false);

  return (
    <div className="flex flex-col h-full bg-background relative overflow-hidden">
      {/* Mode Selector and Connection Status Header */}
      <div className="px-6 py-2.5 border-b border-border/50 bg-background shrink-0 flex items-center justify-between z-10 shadow-sm">
        <div className="flex items-center gap-1.5 font-semibold text-primary">
          <MessageSquare className="w-4 h-4" />
          <span className="text-sm">Metric Build Mode</span>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setIsFileManagerOpen(true)}
            className="h-7 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            <FolderOpen className="w-3.5 h-3.5 mr-1.5" />
            Manage Files
          </Button>
          <div className="h-4 w-px bg-border/50 mx-1"></div>
          <span className={`flex h-2 w-2 rounded-full ${isLoading ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500 animate-pulse'}`} />
          <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider font-mono">
            {isLoading ? 'Agent Thinking...' : 'Agent Ready'}
          </span>
        </div>
      </div>

      {/* Main Conversation Feed Timeline */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-50">
            <Bot className="w-12 h-12 text-muted-foreground" />
            <div className="space-y-1">
              <p className="font-semibold text-foreground">Hi! I&apos;m the EvalPlatform Agent.</p>
              <p className="text-sm text-muted-foreground">Describe the evaluation metric you want to build and I&apos;ll configure it instantly.</p>
            </div>
          </div>
        )}
        
        {messages.map((msg) => {
          const content = getMessageContent(msg);
          if (!content) return null;

          return (
            <div key={msg.id} className="space-y-4">
              {/* Standard Chat Message Bubbles */}
              <div className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "ml-auto flex-row-reverse" : ""}`}>
                <div className={`w-8 h-8 rounded-[2px] flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted border"}`}>
                  {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>
                <div className={`px-4 py-3 rounded-[2px] flex flex-col gap-3 ${msg.role === "user" ? "bg-primary text-primary-foreground border border-primary/20 shadow-sm" : "bg-muted/30 border border-border/50 shadow-sm"}`}>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
                  
                  {msg.role === "model" && (
                    <Button 
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => msg.runtime_id ? setSelectedRuntimeId(msg.runtime_id) : toast.error("No runtime ID attached to this message.")}
                      className="self-start text-xs font-semibold shadow-sm h-8 rounded-[2px]"
                      disabled={!msg.runtime_id}
                    >
                      <TestTube className="w-3.5 h-3.5 mr-1.5" />
                      View Runtime & Evaluate
                    </Button>
                  )}
                </div>
              </div>
              
              {/* Tool invocation feedback */}
              {msg.toolInvocations?.map((toolInvocation) => {
                if (toolInvocation.toolName === 'UpdateMetricConfigTool' && 'result' in toolInvocation) {
                  return (
                    <div key={toolInvocation.toolCallId} className="flex gap-3 max-w-[85%]">
                      <div className="w-8 h-8 shrink-0" />
                      <div className="px-4 py-3 rounded-[2px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 flex items-center gap-2 shadow-sm font-medium">
                        <Sparkles className="w-4 h-4" />
                        <p className="text-sm">Agent updated the configuration panel</p>
                      </div>
                    </div>
                  )
                }
                return null;
              })}
            </div>
          );
        })}
        {isLoading && (
          <div className="flex gap-3 max-w-[85%] animate-pulse">
             <div className="w-8 h-8 rounded-[2px] flex items-center justify-center shrink-0 bg-muted border">
               <Bot className="w-4 h-4" />
             </div>
             <div className="px-4 py-3 rounded-[2px] bg-muted/30 border border-border/50 flex items-center gap-1 shadow-sm">
               <span className="w-1.5 h-1.5 rounded-full bg-foreground/50 animate-bounce" />
               <span className="w-1.5 h-1.5 rounded-full bg-foreground/50 animate-bounce delay-75" />
               <span className="w-1.5 h-1.5 rounded-full bg-foreground/50 animate-bounce delay-150" />
             </div>
          </div>
        )}
      </div>
      
      {/* Standard bottom chat bar */}
      <div className="p-4 bg-background border-t border-border/50 shrink-0">
        <form onSubmit={handleSubmit} className="flex relative max-w-3xl mx-auto w-full">
          <Input 
            value={input}
            onChange={handleInputChange}
            placeholder="Tell the agent to redesign the metric... (e.g. Add validation, change scoring scale)" 
            className="pr-12 bg-muted/30 border-border/50 focus-visible:ring-primary/50 rounded-[2px] h-10 shadow-inner"
            disabled={isLoading}
          />
          <Button 
            type="submit" 
            size="icon" 
            className="absolute right-1 top-1 bottom-1 h-auto w-8 rounded-[2px] shadow-sm"
            disabled={!input.trim() || isLoading}
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>

      {/* Runtime Evaluation Modal */}
      <RuntimeInspectorModal 
        runtimeId={selectedRuntimeId}
        metricId={selectedMetricId || null}
        isOpen={!!selectedRuntimeId}
        onClose={() => setSelectedRuntimeId(null)}
        metricConfig={form.getValues()}
      />
      
      {/* File Manager Modal */}
      <FileManagerModal
        isOpen={isFileManagerOpen}
        onClose={() => setIsFileManagerOpen(false)}
      />
    </div>
  )
}
