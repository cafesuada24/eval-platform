import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { PipelineEditor } from "@/components/pipelines/PipelineEditor"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ThresholdConfig {
  fail_over?: number;
  fail_below?: number;
  warning_over?: number;
  warning_below?: number;
}

interface PipelineMetric {
  metric_name: string;
  threshold?: ThresholdConfig;
}

interface Pipeline {
  name: string;
  metrics: PipelineMetric[];
}

interface Metric {
  name: string;
  type: string;
}

async function getPipeline(id: string): Promise<Pipeline | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/pipelines/${id}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    console.error(`Failed to fetch pipeline ${id}:`, error);
    return null;
  }
}

async function getMetrics(): Promise<Metric[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/metrics`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch metrics:", error);
    return [];
  }
}

export default async function PipelineDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  
  const [pipeline, metrics] = await Promise.all([
    getPipeline(id),
    getMetrics()
  ]);

  if (!pipeline) {
    return (
      <div className="p-8 max-w-5xl mx-auto space-y-8 flex flex-col items-center justify-center min-h-[50vh]">
        <h1 className="text-2xl font-bold">Pipeline not found</h1>
        <Link href="/pipelines" className="text-primary hover:underline">Return to pipelines</Link>
      </div>
    );
  }
  
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
        <Link href="/pipelines" className="hover:text-primary transition-colors flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Back to Pipelines
        </Link>
      </div>

      <PipelineEditor initialPipeline={pipeline} availableMetrics={metrics} />
    </div>
  )
}
