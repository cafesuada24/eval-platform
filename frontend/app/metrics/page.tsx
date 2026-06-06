import Link from "next/link";
import Form from "next/form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Pencil, Settings2, Search, Filter } from "lucide-react";
import { DeleteMetricButton } from "@/components/metrics/delete-metric-button";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

import { Metric } from "@/lib/types";

async function getMetrics(): Promise<Metric[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/configs/metrics`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    console.error("Failed to fetch metrics:", error);
    return [];
  }
}

import { PageHeader } from "@/components/ui/page-header";

export default async function MetricsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; type?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const q = resolvedSearchParams.q?.toLowerCase() || "";
  const typeFilter = resolvedSearchParams.type || "all";
  
  let metrics = await getMetrics();

  // Apply filtering
  if (q) {
    metrics = metrics.filter(m => 
      m.name.toLowerCase().includes(q) || 
      (m.description && m.description.toLowerCase().includes(q))
    );
  }
  
  if (typeFilter !== "all") {
    metrics = metrics.filter(m => m.type === typeFilter);
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 flex flex-col h-[calc(100vh-3.5rem)] bg-background">
      <PageHeader 
        preTitle="Evaluation Core"
        title="Metrics Registry"
        description="Manage your primitive and custom AI-judged evaluation metrics."
        actions={
          <Link href="/playground">
            <Button size="sm" className="h-9 shadow-sm rounded-[2px]">
              <Settings2 className="w-4 h-4 mr-2" />
              Create Custom Metric
            </Button>
          </Link>
        }
      />

      <div className="flex flex-col sm:flex-row gap-4 items-center shrink-0 bg-card/20 p-4 rounded-[2px] border border-border/40">
        <Form action="/metrics" className="flex-1 flex gap-3 w-full">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input 
              name="q" 
              placeholder="Search metrics by name or description..." 
              defaultValue={q}
              className="pl-9 h-9 w-full bg-background border-border shadow-sm transition-all focus-visible:ring-1 rounded-[2px] text-xs font-mono"
            />
          </div>
          
          <div className="relative w-40">
            <select
              name="type"
              defaultValue={typeFilter}
              className="h-9 pl-3 pr-8 rounded-[2px] border border-border bg-background text-xs shadow-sm appearance-none focus:outline-none focus:ring-1 focus:ring-ring w-full font-mono"
            >
              <option value="all">All Types</option>
              <option value="ai-judge">AI Judge</option>
              <option value="primitive">Primitive</option>
            </select>
            <Filter className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          </div>

          <Button type="submit" variant="secondary" className="h-9 px-6 font-mono text-xs uppercase tracking-wider shadow-sm rounded-[2px]">
            Search
          </Button>
        </Form>
      </div>

      <div className="border border-border/40 rounded-[2px] bg-card/30 backdrop-blur-xs flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <Table>
            <TableHeader className="bg-muted/50 sticky top-0 z-10 backdrop-blur-md">
              <TableRow className="hover:bg-transparent border-border/50">
                <TableHead className="w-[40%] sm:w-[50%] min-w-[250px]">Name & Description</TableHead>
                <TableHead className="w-[15%] min-w-[100px]">Type</TableHead>
                <TableHead className="w-[20%] min-w-[120px]">Model</TableHead>
                <TableHead className="w-[15%] min-w-[100px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {metrics.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-48 text-center text-muted-foreground">
                    No metrics found matching your criteria.
                  </TableCell>
                </TableRow>
              ) : (
                metrics.map((metric, index) => (
                  <TableRow key={metric.id || metric.name || index} className="border-border/50 transition-colors hover:bg-muted/30 group">
                    <TableCell className="font-medium max-w-[300px] sm:max-w-[400px]">
                      <div className="flex flex-col gap-1.5">
                        <span className="truncate" title={metric.name}>{metric.name}</span>
                        <span className="text-xs text-muted-foreground font-normal truncate" title={metric.description}>
                          {metric.description}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant={metric.type === "primitive" ? "secondary" : "default"}
                        className={metric.type === "ai-judge" ? "bg-primary/10 text-primary hover:bg-primary/20 border-primary/20" : ""}
                      >
                        {metric.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {metric.model_configuration?.model || '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                        {metric.type === "primitive" ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger render={<span tabIndex={0} className="inline-block cursor-not-allowed" />}>
                                <Button variant="ghost" size="icon" disabled className="opacity-50 pointer-events-none">
                                  <Pencil className="w-4 h-4" />
                                  <span className="sr-only">Edit</span>
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent className="bg-secondary text-secondary-foreground border-border/50">
                                <p>System metrics cannot be edited</p>
                              </TooltipContent>
                            </Tooltip>
                            
                            <Tooltip>
                              <TooltipTrigger render={<span tabIndex={0} className="inline-block cursor-not-allowed" />}>
                                <DeleteMetricButton metricId={metric.id} metricName={metric.name} disabled />
                              </TooltipTrigger>
                              <TooltipContent className="bg-secondary text-secondary-foreground border-border/50">
                                <p>System metrics cannot be deleted</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ) : (
                          <>
                            <Link href={`/playground?metric=${metric.name}`}>
                              <Button variant="ghost" size="icon" className="hover:text-primary hover:bg-primary/10">
                                <Pencil className="w-4 h-4" />
                                <span className="sr-only">Edit</span>
                              </Button>
                            </Link>
                            <DeleteMetricButton metricId={metric.id} metricName={metric.name} />
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
