import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { RuntimesLive } from "@/components/runtimes/runtimes-live";

export default function RuntimesPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 flex flex-col h-[calc(100vh-3.5rem)] bg-background">
      <PageHeader
        preTitle="Telemetry Console"
        title="Execution Runtimes"
        description="Inspect, filter, and analyze the individual execution traces and telemetry from your AI pipelines."
      />

      <div className="border border-border/40 rounded-[2px] bg-card/30 backdrop-blur-xs flex-1 overflow-hidden flex flex-col">
        <Suspense fallback={null}>
          <RuntimesLive />
        </Suspense>
      </div>
    </div>
  );
}
