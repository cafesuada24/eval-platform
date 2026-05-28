import Link from "next/link"
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Metric {
  id: string;
  name: string;
  type: string;
  model?: string;
  description: string;
  model_configuration?: any;
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

export default async function MetricsPage() {
  const metrics = await getMetrics();
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Metrics Registry</h1>
          <p className="text-muted-foreground mt-2 text-sm">
            Manage your primitive and custom AI-judged evaluation metrics.
          </p>
        </div>
        <Link href="/playground">
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
            <Settings2 className="w-4 h-4 mr-2" />
            Create Custom Metric
          </Button>
        </Link>
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
            {metrics.map((metric, index) => (
              <TableRow key={metric.id || metric.name || index} className="border-border/50 transition-colors hover:bg-muted/30">
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
                  {metric.model_configuration?.model || metric.model || '-'}
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
                    <Link href={`/playground?metric=${metric.name}`}>
                      <Button variant="ghost" size="icon" className="hover:text-primary hover:bg-primary/10">
                        <Pencil className="w-4 h-4" />
                        <span className="sr-only">Edit</span>
                      </Button>
                    </Link>
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
