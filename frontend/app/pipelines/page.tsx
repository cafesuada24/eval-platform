import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ListTree, Plus } from "lucide-react"

const pipelines = [
  { id: "1", name: "Production Chatbot Evals", description: "Runs weekly regression testing against the main production model." },
  { id: "2", name: "RAG Factuality Pipeline", description: "Evaluates the hallucination rate of retrieved contexts." },
]

export default function PipelinesPage() {
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
          {pipelines.map((pipeline) => (
            <Link key={pipeline.id} href={`/pipelines/${pipeline.id}`}>
              <Card className="hover:border-primary/50 transition-colors bg-card/50 backdrop-blur-sm cursor-pointer group">
                <CardHeader>
                  <CardTitle className="group-hover:text-primary transition-colors flex items-center justify-between">
                    {pipeline.name}
                    <ListTree className="w-4 h-4 text-muted-foreground opacity-50 group-hover:opacity-100 transition-opacity" />
                  </CardTitle>
                  <CardDescription className="line-clamp-2">
                    {pipeline.description}
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
