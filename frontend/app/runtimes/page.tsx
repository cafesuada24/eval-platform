import { getRuntimes } from "@/lib/api/runtimes";
import { RuntimeTable } from "@/components/runtimes/runtime-table";
import { Terminal } from "lucide-react";

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
    <div className="flex flex-col h-full bg-background p-6 lg:p-10">
      <div className="flex flex-col gap-2 mb-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Terminal className="size-5" />
          </div>
          <h1 className="text-3xl font-medium tracking-tight">Execution Runtimes</h1>
        </div>
        <p className="text-muted-foreground text-base max-w-2xl mt-1">
          Inspect, filter, and analyze the individual execution traces and telemetry from your AI pipelines.
        </p>
      </div>

      <div className="flex-1 bg-card rounded-2xl border shadow-sm flex flex-col min-h-0 overflow-hidden">
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
