"use client"
// @ts-nocheck

import { Send, Bot, User, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
interface AgentChatProps {
  messages: any[]
  input: string
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void
  isLoading?: boolean
}

const getMessageContent = (msg: any) => {
  if (msg.content) return msg.content;
  if (msg.parts && Array.isArray(msg.parts)) {
    return msg.parts.map((p: any) => p.text || '').join('');
  }
  return '';
};

export function AgentChat({ messages, input, handleInputChange, handleSubmit, isLoading }: AgentChatProps) {
  return (
    <div className="flex flex-col h-full bg-background relative overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-50">
            <Bot className="w-12 h-12 text-muted-foreground" />
            <div className="space-y-1">
              <p className="font-medium text-foreground">Hi! I'm the EvalPlatform Agent.</p>
              <p className="text-sm text-muted-foreground">Describe the metric you want to build and I'll configure it for you.</p>
            </div>
          </div>
        )}
        
        {messages.map((msg) => (
          <div key={msg.id} className="space-y-4">
            {msg.role !== 'system' && getMessageContent(msg) && (
              <div className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "ml-auto flex-row-reverse" : ""}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                  {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>
                <div className={`px-4 py-3 rounded-2xl ${msg.role === "user" ? "bg-primary text-primary-foreground rounded-tr-sm" : "bg-muted/50 border border-border/50 rounded-tl-sm"}`}>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{getMessageContent(msg)}</p>
                </div>
              </div>
            )}
            
            {/* Tool invocation feedback */}
            {msg.toolInvocations?.map((toolInvocation: any) => {
              if (toolInvocation.toolName === 'UpdateMetricConfigTool' && 'result' in toolInvocation) {
                return (
                  <div key={toolInvocation.toolCallId} className="flex gap-3 max-w-[85%]">
                    <div className="w-8 h-8 shrink-0" />
                    <div className="px-4 py-3 rounded-2xl bg-primary/10 border border-primary/20 text-primary rounded-tl-sm flex items-center gap-2">
                      <Sparkles className="w-4 h-4" />
                      <p className="text-sm font-medium">Agent updated the configuration panel</p>
                    </div>
                  </div>
                )
              }
              return null;
            })}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3 max-w-[85%]">
             <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-muted">
               <Bot className="w-4 h-4" />
             </div>
             <div className="px-4 py-3 rounded-2xl bg-muted/50 border border-border/50 rounded-tl-sm flex items-center gap-1">
               <span className="w-1.5 h-1.5 rounded-full bg-foreground/50 animate-bounce" />
               <span className="w-1.5 h-1.5 rounded-full bg-foreground/50 animate-bounce delay-75" />
               <span className="w-1.5 h-1.5 rounded-full bg-foreground/50 animate-bounce delay-150" />
             </div>
          </div>
        )}
      </div>
      
      <div className="p-4 bg-background border-t border-border/50">
        <form onSubmit={handleSubmit} className="flex relative">
          <Input 
            value={input}
            onChange={handleInputChange}
            placeholder="E.g., Make it a boolean metric returning 1 for correct JSON, and rename it to format check" 
            className="pr-12 bg-muted/30 border-border/50 focus-visible:ring-primary/50 rounded-full"
            disabled={isLoading}
          />
          <Button 
            type="submit" 
            size="icon" 
            className="absolute right-1 top-1 bottom-1 h-auto w-8 rounded-full"
            disabled={!input.trim() || isLoading}
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}
