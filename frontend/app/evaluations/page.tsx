import { Suspense } from "react";
import Form from "next/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { EvaluationsTable } from "@/components/evaluations/evaluations-table";

export const dynamic = "force-dynamic";

export default async function EvaluationsPage(props: {
  searchParams: Promise<{ q?: string }>;
}) {
  const searchParams = await props.searchParams;
  const q = searchParams.q || "";

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 bg-background">
      <PageHeader
        preTitle="Evaluation Workspace"
        title="Batch Run Logs"
        description="View all recent evaluation batches, execution timestamps, and their overarching pass rates."
      />

      <div className="flex flex-col sm:flex-row gap-4 items-center shrink-0 bg-card/20 p-4 rounded-[2px] border border-border/40">
        <Form action="/evaluations" className="flex w-full max-w-sm gap-2">
          <Input
            name="q"
            defaultValue={q}
            placeholder="Search by ID or name..."
            className="flex-1 rounded-[2px] border-border text-xs font-mono h-9"
          />
          <Button type="submit" variant="secondary" className="rounded-[2px] font-mono text-[10px] uppercase tracking-wider h-9 px-4">
            Search
          </Button>
        </Form>
      </div>

      <Suspense fallback={null}>
        <EvaluationsTable />
      </Suspense>
    </div>
  );
}
