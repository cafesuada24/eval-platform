import { Dataset } from "@/lib/types"
import { UploadDatasetDialog } from "@/components/datasets/UploadDatasetDialog"
import { CreateDatasetDialog } from "@/components/datasets/CreateDatasetDialog"
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

import { PageHeader } from "@/components/ui/page-header"

export default async function DatasetsPage() {
  const datasets = await getDatasets();

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 bg-background">
      <PageHeader 
        preTitle="Data Workspace"
        title="Data Core"
        description="Centralized repository for evaluation test cases. Ingest, inspect, and manage foundational data powering your semantic pipelines."
        actions={
          <>
            <UploadDatasetDialog />
            <CreateDatasetDialog />
          </>
        }
      />

      {/* Bento Grid List */}
      <DatasetListClient datasets={datasets} />
    </div>
  )
}
