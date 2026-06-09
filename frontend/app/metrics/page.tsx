import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Settings2 } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { MetricsBrowserClient } from "@/components/metrics/MetricsBrowserClient";
import { Metric } from "@/lib/types";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getMetrics(): Promise<Metric[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/configs/metrics`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch metrics:", error);
    return [];
  }
}

export default async function MetricsPage() {
  const metrics = await getMetrics();

  return (
    <div className="p-8 w-full flex flex-col h-[calc(100vh-3.5rem)] gap-6 bg-background">
      <PageHeader
        preTitle="Evaluation Core"
        title="Metrics Registry"
        description="Browse and manage your primitive and AI-judged evaluation metrics."
        actions={
          <Link href="/playground">
            <Button size="sm" className="h-9 shadow-sm rounded-[2px]">
              <Settings2 className="w-4 h-4 mr-2" />
              Create Custom Metric
            </Button>
          </Link>
        }
      />
      <MetricsBrowserClient metrics={metrics} />
    </div>
  );
}
