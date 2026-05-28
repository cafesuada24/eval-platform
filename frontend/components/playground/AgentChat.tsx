"use client"

import { useState } from "react"
import { Send, Bot, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

// Mock messages for Phase 3 (We integrate Vercel AI SDK in Phase 4)
export function AgentChat() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState([
    { id: 1, role: "assistant", content: "Hi! I'm the EvalPlatform Agent. How can I help you design your metric today?" }
  ])

  const handleSend = () => {
    if (!input.trim()) return
    setMessages([...messages, { id: Date.now(), role: "user", content: input }])
    setInput("")
  }

  return (
    <div className="flex flex-col h-full bg-background relative overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "ml-auto flex-row-reverse" : ""}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
              {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>
            <div className={`px-4 py-3 rounded-2xl ${msg.role === "user" ? "bg-primary text-primary-foreground rounded-tr-sm" : "bg-muted/50 border border-border/50 rounded-tl-sm"}`}>
              <p className="text-sm leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}
      </div>
      
      <div className="p-4 bg-background border-t border-border/50">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex relative">
          <Input 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe the metric you want to build..." 
            className="pr-12 bg-muted/30 border-border/50 focus-visible:ring-primary/50 rounded-full"
          />
          <Button 
            type="submit" 
            size="icon" 
            className="absolute right-1 top-1 bottom-1 h-auto w-8 rounded-full"
            disabled={!input.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}
