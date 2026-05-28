import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Save, Play } from "lucide-react"
import { PipelineMetricCard } from "@/components/pipelines/PipelineMetricCard"

// Mock data
const pipeline = {
  id: "1",
  name: "Production Chatbot Evals",
  description: "Runs weekly regression testing against the main production model to catch regressions in toxicity and relevance.",
  metrics: [
    { id: "m1", name: "Exact Match", type: "primitive" as const, description: "Ensures the specific output string matches ground truth exactly." },
    { id: "m2", name: "Toxicity Judge", type: "custom" as const, model: "gemini-2.5-pro", description: "Evaluates the toxicity of the response using advanced semantic criteria." },
    { id: "m3", name: "Relevance Scorer", type: "custom" as const, model: "gemini-2.5-flash", description: "Scores the relevance of the output to the initial user prompt on a scale of 1-5." }
  ]
}

export default function PipelineDetailPage({ params }: { params: { id: string } }) {
  // In a real app we'd fetch by params.id
  
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
        <Link href="/pipelines" className="hover:text-primary transition-colors flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Back to Pipelines
        </Link>
      </div>

      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight text-foreground">{pipeline.name}</h1>
          <p className="text-muted-foreground text-lg max-w-2xl">
            {pipeline.description}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="border-border/50 bg-card/50 backdrop-blur-sm">
            <Save className="w-4 h-4 mr-2" />
            Save Draft
          </Button>
          <Button className="bg-primary text-primary-foreground shadow-lg shadow-primary/20">
            <Play className="w-4 h-4 mr-2" />
            Run Evaluation
          </Button>
        </div>
      </div>

      <div className="mt-12 space-y-6">
        <div className="flex items-center justify-between border-b border-border/50 pb-4">
          <h2 className="text-2xl font-semibold tracking-tight">Active Metrics</h2>
          <Button variant="ghost" size="sm" className="text-primary hover:text-primary hover:bg-primary/10">
            + Add Metric
          </Button>
        </div>

        <div className="grid gap-6">
          {pipeline.metrics.map((metric) => (
            <PipelineMetricCard
              key={metric.id}
              name={metric.name}
              description={metric.description}
              type={metric.type}
              model={metric.model}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
