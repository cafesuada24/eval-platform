import { Dataset } from "@/lib/types"
import { DatasetDetailClient } from "@/components/datasets/DatasetDetailClient"
import Link from "next/link"
import { ArrowLeft, Database } from "lucide-react"

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getDataset(id: string): Promise<Dataset | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/datasets/${id}`, { cache: 'no-store' });
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return res.json();
  } catch (error) {
    console.error("Failed to fetch dataset:", error);
    return null;
  }
}

interface Props {
  params: Promise<{ id: string }>;
}

export default async function DatasetDetailPage({ params }: Props) {
  const { id } = await params;
  const dataset = await getDataset(id);

  if (!dataset) {
    return (
      <div className="min-h-full bg-background flex flex-col items-center justify-center p-8">
        <div className="max-w-md text-center space-y-6">
          <Database className="w-16 h-16 text-muted-foreground mx-auto" />
          <h1 className="text-4xl font-bold tracking-tight text-foreground">Not Found</h1>
          <p className="text-muted-foreground font-mono">Dataset {id} could not be located in the core.</p>
          <Link href="/datasets" className="inline-flex items-center text-primary hover:text-primary/80 transition-colors">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Return to Core
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-12">
        {/* Navigation & Header */}
        <div className="space-y-8">
          <Link 
            href="/datasets" 
            className="inline-flex items-center text-sm font-mono tracking-widest uppercase text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Index
          </Link>

          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-8 border-b border-border/50">
            <div className="space-y-4">
              <h1 className="text-5xl lg:text-6xl font-extrabold tracking-tighter text-foreground">
                {dataset.name}
              </h1>
              <div className="flex flex-wrap items-center gap-4">
                <span className="font-mono text-sm text-muted-foreground bg-secondary border border-border px-3 py-1 rounded-full">
                  ID: {dataset.id}
                </span>
                <span className="font-mono text-sm text-primary bg-primary/10 border border-primary/20 px-3 py-1 rounded-full">
                  {dataset.cases?.length || 0} CASES
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Rows Client Component */}
        <DatasetDetailClient dataset={dataset} />
      </div>
    </div>
  )
}
