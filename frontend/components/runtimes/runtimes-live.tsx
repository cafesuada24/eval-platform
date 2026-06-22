"use client";

import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import { swrFetcher } from "@/hooks/use-swr-fetcher";
import { RuntimeState } from "@/lib/types";
import { RuntimeTable } from "@/components/runtimes/runtime-table";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";
const PAGE_SIZE = 12;

export function RuntimesLive() {
  const searchParams = useSearchParams();
  const q = searchParams.get("q") || "";
  const sort = searchParams.get("sort") || "desc";
  const page = parseInt(searchParams.get("page") || "1", 10);

  const { data: runtimes = [] } = useSWR<RuntimeState[]>(
    `${API_BASE}/runtimes`,
    swrFetcher,
    { refreshInterval: 3000 }
  );

  const getFirstEventTime = (events: RuntimeState["events"]) => {
    if (!events || events.length === 0) return 0;
    return Math.min(...events.map((e) => new Date(e.timestamp).getTime()));
  };

  let filtered = runtimes;
  if (q) {
    const qLower = q.toLowerCase();
    filtered = filtered.filter((r) => r.runtime_id.toLowerCase().includes(qLower));
  }

  filtered = [...filtered].sort((a, b) => {
    const aTime = getFirstEventTime(a.events);
    const bTime = getFirstEventTime(b.events);
    return sort === "asc" ? aTime - bTime : bTime - aTime;
  });

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
  const safePage = Math.max(1, Math.min(page, totalPages));
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <RuntimeTable
      data={paginated}
      total={filtered.length}
      page={safePage}
      pageSize={PAGE_SIZE}
      totalPages={totalPages}
      q={q}
      sort={sort}
    />
  );
}
