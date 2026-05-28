import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ListTree, Plus } from "lucide-react"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Pipeline {
  name: string;
  metrics?: any[];
}

async function getPipelines(): Promise<Pipeline[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/pipelines`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch pipelines:", error);
    return [];
  }
}

export default async function PipelinesPage() {
  const pipelines = await getPipelines();
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Observability Pipelines</h1>
          <p className="text-muted-foreground mt-2 text-sm">
            Configure automated evaluation rulesets and thresholds.
          </p>
        </div>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          New Pipeline
        </Button>
      </div>

      {pipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 border border-dashed border-border/50 rounded-xl bg-card/10">
          <ListTree className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
          <h3 className="text-lg font-medium">No pipelines found</h3>
          <p className="text-sm text-muted-foreground mt-1 mb-4 text-center max-w-md">
            Create your first observability pipeline to start evaluating traces and tracking semantic thresholds over time.
          </p>
          <Button variant="outline">Create Pipeline</Button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {pipelines.map((pipeline, index) => (
            <Link key={`${pipeline.name}-${index}`} href={`/pipelines/${pipeline.name}`}>
              <Card className="hover:border-primary/50 transition-colors bg-card/50 backdrop-blur-sm cursor-pointer group">
                <CardHeader>
                  <CardTitle className="group-hover:text-primary transition-colors flex items-center justify-between">
                    {pipeline.name}
                    <ListTree className="w-4 h-4 text-muted-foreground opacity-50 group-hover:opacity-100 transition-opacity" />
                  </CardTitle>
                  <CardDescription>
                    {pipeline.metrics?.length || 0} configured metrics
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
