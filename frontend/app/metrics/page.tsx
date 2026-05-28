import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Pencil, Settings2 } from "lucide-react"

const metrics = [
  { id: "1", name: "Exact Match", type: "primitive", model: "-", description: "System level exact string match." },
  { id: "2", name: "Toxicity Judge", type: "custom", model: "gemini-2.5-pro", description: "Evaluates the toxicity of the response." },
  { id: "3", name: "JSON Validator", type: "primitive", model: "-", description: "Validates JSON structure." },
  { id: "4", name: "Relevance Scorer", type: "custom", model: "gemini-2.5-flash", description: "Scores the relevance of the output to the prompt." },
]

export default function MetricsPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Metrics Registry</h1>
          <p className="text-muted-foreground mt-2 text-sm">
            Manage your primitive and custom AI-judged evaluation metrics.
          </p>
        </div>
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
          <Settings2 className="w-4 h-4 mr-2" />
          Create Custom Metric
        </Button>
      </div>

      <div className="border border-border/50 rounded-xl bg-card/50 backdrop-blur-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow className="hover:bg-transparent border-border/50">
              <TableHead className="w-[250px]">Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Model</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {metrics.map((metric) => (
              <TableRow key={metric.id} className="border-border/50 transition-colors hover:bg-muted/30">
                <TableCell className="font-medium">
                  <div className="flex flex-col gap-1">
                    <span>{metric.name}</span>
                    <span className="text-xs text-muted-foreground font-normal">{metric.description}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge 
                    variant={metric.type === "primitive" ? "secondary" : "default"}
                    className={metric.type === "custom" ? "bg-primary/20 text-primary hover:bg-primary/30 border-primary/30" : ""}
                  >
                    {metric.type}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {metric.model}
                </TableCell>
                <TableCell className="text-right">
                  {metric.type === "primitive" ? (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger render={<span tabIndex={0} />}>
                          <Button variant="ghost" size="icon" disabled className="opacity-50">
                            <Pencil className="w-4 h-4" />
                            <span className="sr-only">Edit</span>
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent className="bg-secondary text-secondary-foreground border-border/50">
                          <p>System metrics cannot be edited</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  ) : (
                    <Button variant="ghost" size="icon" className="hover:text-primary hover:bg-primary/10">
                      <Pencil className="w-4 h-4" />
                      <span className="sr-only">Edit</span>
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
