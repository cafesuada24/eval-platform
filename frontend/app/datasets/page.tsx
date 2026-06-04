import { Dataset } from "@/lib/types"
import { UploadDatasetDialog } from "@/components/datasets/UploadDatasetDialog"
import { DatasetListClient } from "@/components/datasets/DatasetListClient"

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getDatasets(): Promise<Dataset[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/datasets/`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch datasets:", error);
    return [];
  }
}

export default async function DatasetsPage() {
  const datasets = await getDatasets();

  return (
    <div className="min-h-full bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-12">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-8 border-b border-border/50">
          <div className="space-y-3 max-w-2xl">
            <h1 className="text-5xl font-extrabold tracking-tighter text-foreground">
              Data Core
            </h1>
            <p className="text-muted-foreground text-lg leading-relaxed max-w-xl">
              Centralized repository for evaluation test cases. Ingest, inspect, and manage foundational data powering your semantic pipelines.
            </p>
          </div>
          <UploadDatasetDialog />
        </div>

        {/* Bento Grid List */}
        <DatasetListClient datasets={datasets} />
      </div>
    </div>
  )
}
