import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { AgentChat } from "@/components/playground/AgentChat"
import { MetricConfigurator } from "@/components/playground/MetricConfigurator"

export default function PlaygroundPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      <div className="flex items-center px-4 py-2 border-b border-border/50 bg-background shrink-0">
        <h1 className="text-sm font-semibold tracking-tight">Metric Playground</h1>
        <div className="ml-auto flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs text-muted-foreground font-medium">Agent Connected</span>
        </div>
      </div>

      <ResizablePanelGroup orientation="horizontal" className="flex-1 overflow-hidden">
        <ResizablePanel defaultSize={40} minSize={25} className="flex flex-col h-full bg-background relative">
          <AgentChat />
        </ResizablePanel>
        
        <ResizableHandle className="w-1.5 bg-border/50 hover:bg-primary/50 transition-colors data-[resize-handle-state=drag]:bg-primary" />
        
        <ResizablePanel defaultSize={60} minSize={30} className="flex flex-col h-full bg-card/30">
          <MetricConfigurator />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
