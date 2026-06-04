"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PipelineRunResult } from "@/lib/api/evaluations";
import { RunStatusBadge } from "./run-status-badge";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PipelineResultsTableProps {
  results: PipelineRunResult[];
}

export function PipelineResultsTable({ results }: PipelineResultsTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (runId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(runId)) {
      newExpanded.delete(runId);
    } else {
      newExpanded.add(runId);
    }
    setExpandedRows(newExpanded);
  };

  return (
    <div className="border rounded-md">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="w-10"></TableHead>
            <TableHead>Run ID</TableHead>
            <TableHead>Testcase ID</TableHead>
            <TableHead className="text-right">Overall Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground h-32">
                No pipeline results found.
              </TableCell>
            </TableRow>
          ) : (
            results.map((run) => {
              const isExpanded = expandedRows.has(run.run_id);
              return (
                <div key={run.run_id} className="contents">
                  <TableRow
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => toggleRow(run.run_id)}
                  >
                    <TableCell>
                      <Button variant="ghost" size="icon" className="h-6 w-6">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="font-medium font-mono text-xs">
                      {run.run_id.split("-")[0]}...
                    </TableCell>
                    <TableCell className="text-muted-foreground font-mono text-xs">
                      {run.testcase_id ? `${run.testcase_id.split("-")[0]}...` : "N/A"}
                    </TableCell>
                    <TableCell className="text-right">
                      <RunStatusBadge status={run.overall_status} />
                    </TableCell>
                  </TableRow>
                  {isExpanded && (
                    <TableRow className="bg-muted/20 hover:bg-muted/20">
                      <TableCell colSpan={4} className="p-0">
                        <div className="p-4 border-b">
                          <h4 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">
                            Metric Results
                          </h4>
                          {run.metric_results.length === 0 ? (
                            <p className="text-xs text-muted-foreground">No metrics found.</p>
                          ) : (
                            <div className="space-y-3">
                              {run.metric_results.map((metric) => (
                                <div
                                  key={metric.metric_id}
                                  className="flex items-start justify-between bg-background border p-3 rounded-md"
                                >
                                  <div className="flex-1 pr-4">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="font-medium text-sm">
                                        Metric: {metric.metric_id.split("-")[0]}
                                      </span>
                                      <RunStatusBadge status={metric.assertion_status} className="text-[10px] h-5 px-2" />
                                    </div>
                                    <p className="text-xs text-muted-foreground line-clamp-2 hover:line-clamp-none transition-all">
                                      {metric.justification || "No justification provided."}
                                    </p>
                                  </div>
                                  <div className="text-right flex flex-col items-end justify-center h-full">
                                    <span className="text-xs text-muted-foreground mb-1">Score</span>
                                    <span className="font-bold font-mono">
                                      {metric.score.toFixed(2)}
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </div>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}
