import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Settings2 } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { MetricsBrowserClient } from "@/components/metrics/MetricsBrowserClient";

export const dynamic = "force-dynamic";

export default function MetricsPage() {
  return (
    <div className="p-8 w-full flex flex-col h-[calc(100vh-3.5rem)] gap-6 bg-background">
      <PageHeader
        preTitle="Evaluation Core"
        title="Metrics Registry"
        description="Browse and manage your primitive and AI-judged evaluation metrics."
        actions={
          <Link href="/metric-builder">
            <Button size="sm" className="h-9 shadow-sm rounded-[2px]">
              <Settings2 className="w-4 h-4 mr-2" />
              Create Custom Metric
            </Button>
          </Link>
        }
      />
      <MetricsBrowserClient />
    </div>
  );
}
