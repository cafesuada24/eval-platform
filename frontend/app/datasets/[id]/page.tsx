import React from "react";
import { DatasetWorkspace } from "@/components/datasets/DatasetWorkspace";
import { fetchDataset } from "@/lib/api/datasets";
import { Metadata } from "next";

interface DatasetPageProps {
  params: {
    id: string;
  };
}

export async function generateMetadata({ params }: DatasetPageProps): Promise<Metadata> {
  try {
    const resolvedParams = await params;
    // Note: Since this is a server component, fetchDataset would need to be able to make 
    // an absolute URL fetch to the API if this is during SSR, but for simplicity we'll assume
    // either it's mocked or we can just set a static title for now since `fetch` with relative URL 
    // fails in Next.js Server Components. In a real app we'd fetch directly from DB or absolute URL.
    return {
      title: `Dataset ${resolvedParams.id} | EvalPlatform`,
    };
  } catch (error) {
    return {
      title: "Dataset Not Found",
    };
  }
}

export default async function DatasetPage({ params }: DatasetPageProps) {
  const resolvedParams = await params;
  
  try {
    const dataset = await fetchDataset(resolvedParams.id);

    return (
      <main className="w-full h-screen bg-background">
        <DatasetWorkspace dataset={dataset} />
      </main>
    );
  } catch (error) {
    return (
      <main className="w-full h-screen bg-background flex items-center justify-center text-muted-foreground">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold text-foreground">Dataset Not Found</h1>
          <p>The dataset you are looking for does not exist or could not be loaded.</p>
        </div>
      </main>
    );
  }
}
