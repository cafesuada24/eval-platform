"use client"

import { useState } from "react"
import { MetricsList } from "@/components/metrics/MetricsList"
import { MetricDetail } from "@/components/metrics/MetricDetail"
import { Metric } from "@/lib/types"
import useSWR from "swr"
import { swrFetcher } from "@/hooks/use-swr-fetcher"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1"

export function MetricsBrowserClient() {
  const { data: metrics = [] } = useSWR<Metric[]>(
    `${API_BASE}/configs/metrics`,
    swrFetcher,
    { refreshInterval: 5000 }
  )

  const [selectedId, setSelectedId] = useState<string | null>(null)

  // Determine actual selected ID
  const stillExists = metrics.some((m) => m.id === selectedId)
  const targetId = stillExists ? selectedId : (metrics[0]?.id ?? null)

  if (selectedId !== targetId) {
    setSelectedId(targetId)
  }

  const selectedMetric = metrics.find((m) => m.id === targetId) ?? null

  return (
    <div className="flex flex-col md:flex-row flex-1 min-h-0 border border-border/40 rounded-[2px] bg-card/30 backdrop-blur-xs overflow-hidden">
      <div className="w-full h-[320px] md:h-full md:w-[35%] md:min-w-[280px] shrink-0">
        <MetricsList
          metrics={metrics}
          selectedId={targetId}
          onSelect={setSelectedId}
          className="border-r-0 md:border-r border-b md:border-b-0 border-border/40"
        />
      </div>
      <div className="flex-1 min-w-0">
        <MetricDetail metric={selectedMetric} />
      </div>
    </div>
  )
}
