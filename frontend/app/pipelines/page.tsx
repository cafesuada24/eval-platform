import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { PipelinesGrid } from "@/components/pipelines/pipelines-grid";

export const dynamic = "force-dynamic";

export default function PipelinesPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 bg-background">
      <PageHeader
        preTitle="Evaluation Core"
        title="Observability Pipelines"
        description="Configure automated evaluation rulesets and thresholds."
        actions={
          <Link href="/pipelines/new">
            <Button size="sm" className="h-9 rounded-[2px] shadow-sm">
              <Plus className="w-4 h-4 mr-2" />
              New Pipeline
            </Button>
          </Link>
        }
      />

      <PipelinesGrid />
    </div>
  );
}
