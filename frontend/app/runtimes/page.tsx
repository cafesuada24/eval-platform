import { getRuntimes } from "@/lib/api/runtimes";
import { RuntimeTable } from "@/components/runtimes/runtime-table";
import { Terminal } from "lucide-react";

import { PageHeader } from "@/components/ui/page-header";

export default async function RuntimesPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}) {
  const runtimes = await getRuntimes().catch(() => []);
  const resolvedSearchParams = await searchParams;
  
  const q = typeof resolvedSearchParams.q === "string" ? resolvedSearchParams.q : "";
  const sort = typeof resolvedSearchParams.sort === "string" ? resolvedSearchParams.sort : "desc";
  const page = typeof resolvedSearchParams.page === "string" ? parseInt(resolvedSearchParams.page, 10) : 1;

  let filtered = runtimes;
  if (q) {
    const qLower = q.toLowerCase();
    filtered = filtered.filter(r => 
      r.runtime_id.toLowerCase().includes(qLower)
    );
  }

  filtered.sort((a, b) => {
    const getFirstEventTime = (events: typeof a.events) => {
      if (!events || events.length === 0) return 0;
      return Math.min(...events.map(e => new Date(e.timestamp).getTime()));
    };

    const aTime = getFirstEventTime(a.events);
    const bTime = getFirstEventTime(b.events);
    return sort === "asc" ? aTime - bTime : bTime - aTime;
  });

  const pageSize = 12;
  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const safePage = Math.max(1, Math.min(page, totalPages));
  const paginated = filtered.slice((safePage - 1) * pageSize, safePage * pageSize);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 flex flex-col h-[calc(100vh-3.5rem)] bg-background">
      <PageHeader 
        preTitle="Telemetry Console"
        title="Execution Runtimes"
        description="Inspect, filter, and analyze the individual execution traces and telemetry from your AI pipelines."
      />

      <div className="border border-border/40 rounded-[2px] bg-card/30 backdrop-blur-xs flex-1 overflow-hidden flex flex-col">
        <RuntimeTable 
          data={paginated} 
          total={filtered.length} 
          page={safePage} 
          pageSize={pageSize} 
          totalPages={totalPages}
          q={q}
          sort={sort}
        />
      </div>
    </div>
  );
}
