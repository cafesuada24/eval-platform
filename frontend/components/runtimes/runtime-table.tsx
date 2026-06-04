"use client";

import React, { useState } from "react";
import Form from "next/form";
import { RuntimeState } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Search, SlidersHorizontal, ArrowUpDown, Clock, ActivitySquare, ChevronLeft, ChevronRight, ChevronDown, Zap, Database, DollarSign, ListTree } from "lucide-react";
import Link from "next/link";

interface RuntimeTableProps {
  data: RuntimeState[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  q: string;
  sort: string;
}

export function RuntimeTable({ data, total, page, totalPages, q, sort }: RuntimeTableProps) {
  const [selectedRuntime, setSelectedRuntime] = useState<RuntimeState | null>(null);
  const [expandedEventIdx, setExpandedEventIdx] = useState<number | null>(null);

  // Removed getStatusColor since status isn't in the new schema

  return (
    <div className="flex flex-col h-full w-full">
      {/* Toolbar */}
      <div className="p-4 border-b flex items-center justify-between gap-4 bg-muted/20">
        <Form action="/runtimes" className="flex items-center gap-3 w-full max-w-2xl">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input 
              name="q" 
              placeholder="Search by trace ID or status..." 
              defaultValue={q}
              className="pl-9 h-10 w-full bg-background border-muted shadow-sm transition-all focus-visible:ring-1"
            />
          </div>
          
          <div className="relative">
            <select
              name="sort"
              defaultValue={sort}
              className="h-10 pl-3 pr-8 rounded-md border border-muted bg-background text-sm shadow-sm appearance-none focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </select>
            <ArrowUpDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          </div>

          <Button type="submit" variant="secondary" className="h-10 px-6 font-medium shadow-sm">
            Filter
          </Button>
        </Form>
        <div className="text-sm text-muted-foreground font-medium">
          {total} {total === 1 ? "trace" : "traces"}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader className="bg-muted/30 sticky top-0 backdrop-blur-sm z-10">
            <TableRow className="hover:bg-transparent">
              <TableHead className="font-medium">Runtime ID</TableHead>
              <TableHead className="font-medium">Timestamp</TableHead>
              <TableHead className="font-medium text-center">Events</TableHead>
              <TableHead className="text-right font-medium">Total Tokens</TableHead>
              <TableHead className="text-right font-medium">Latency</TableHead>
              <TableHead className="text-right font-medium">Cost</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="h-48 text-center text-muted-foreground">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <ActivitySquare className="h-8 w-8 text-muted-foreground/40" />
                    <p>No runtimes found.</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              data.map((rt, index) => (
                <TableRow 
                  key={rt.runtime_id ? `${rt.runtime_id}-${index}` : `runtime-${index}`} 
                  className="cursor-pointer group transition-colors hover:bg-muted/40"
                  onClick={() => setSelectedRuntime(rt)}
                >
                  <TableCell className="font-mono text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                    {rt.runtime_id}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Clock className="h-3 w-3" />
                      {rt.events && rt.events.length > 0 
                        ? new Date(Math.min(...rt.events.map(e => new Date(e.timestamp).getTime()))).toLocaleString() 
                        : "N/A"}
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className="bg-background">
                      {rt.events?.length || 0}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {rt.usage ? (rt.usage.input_tokens + rt.usage.output_tokens).toLocaleString() : "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {rt.usage?.latency_ms !== undefined ? `${rt.usage.latency_ms}ms` : "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm font-mono text-muted-foreground">
                    {rt.usage?.estimated_cost_usd !== undefined ? `$${rt.usage.estimated_cost_usd.toFixed(6)}` : "—"}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="p-4 border-t flex items-center justify-between bg-muted/10">
        <div className="text-sm text-muted-foreground font-medium">
          Page {page} of {totalPages}
        </div>
        <div className="flex items-center gap-2">
          <Link 
            href={`/runtimes?q=${encodeURIComponent(q)}&sort=${sort}&page=${page - 1}`}
            className={page <= 1 ? "pointer-events-none opacity-50 inline-flex h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] items-center justify-center border-border bg-background transition-all outline-none" : "inline-flex h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] items-center justify-center border-border bg-background hover:bg-muted hover:text-foreground transition-all outline-none"}
            style={page <= 1 ? { pointerEvents: "none", opacity: 0.5 } : undefined}
          >
            <ChevronLeft className="h-4 w-4 mr-1" /> Previous
          </Link>
          <Link 
            href={`/runtimes?q=${encodeURIComponent(q)}&sort=${sort}&page=${page + 1}`}
            className={page >= totalPages ? "pointer-events-none opacity-50 inline-flex h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] items-center justify-center border-border bg-background transition-all outline-none" : "inline-flex h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] items-center justify-center border-border bg-background hover:bg-muted hover:text-foreground transition-all outline-none"}
            style={page >= totalPages ? { pointerEvents: "none", opacity: 0.5 } : undefined}
          >
            Next <ChevronRight className="h-4 w-4 ml-1" />
          </Link>
        </div>
      </div>

      {/* Detail Dialog */}
      <Dialog 
        open={!!selectedRuntime} 
        onOpenChange={(open) => {
          if (!open) {
            setSelectedRuntime(null);
            setExpandedEventIdx(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-5xl w-[90vw] max-h-[90vh] overflow-hidden flex flex-col p-0 gap-0 border-muted rounded-xl shadow-2xl">
          <DialogHeader className="p-6 pb-4 border-b bg-muted/10">
            <div className="flex items-center justify-between pr-6">
              <DialogTitle className="text-xl flex items-center gap-3">
                Trace Details
              </DialogTitle>
            </div>
            <DialogDescription className="font-mono text-xs mt-2 text-muted-foreground">
              ID: {selectedRuntime?.runtime_id}
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-8 bg-background">
            {/* Resource Usage */}
            <div className="space-y-3">
              <div className="text-xs font-semibold text-muted-foreground tracking-wider uppercase flex items-center gap-2">
                <ActivitySquare className="h-3 w-3" /> Resource Usage
              </div>
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-muted/30 p-4 rounded-xl border flex flex-col gap-1">
                  <div className="text-xs text-muted-foreground flex items-center gap-1.5"><Clock className="h-3 w-3"/> Latency</div>
                  <div className="font-medium">{selectedRuntime?.usage?.latency_ms !== undefined ? `${selectedRuntime.usage.latency_ms}ms` : "—"}</div>
                </div>
                <div className="bg-muted/30 p-4 rounded-xl border flex flex-col gap-1">
                  <div className="text-xs text-muted-foreground flex items-center gap-1.5"><Zap className="h-3 w-3"/> Tokens</div>
                  <div className="font-medium">{selectedRuntime?.usage ? (selectedRuntime.usage.input_tokens + selectedRuntime.usage.output_tokens).toLocaleString() : "—"}</div>
                </div>
                <div className="bg-muted/30 p-4 rounded-xl border flex flex-col gap-1">
                  <div className="text-xs text-muted-foreground flex items-center gap-1.5"><DollarSign className="h-3 w-3"/> Cost</div>
                  <div className="font-medium">{selectedRuntime?.usage?.estimated_cost_usd !== undefined ? `$${selectedRuntime.usage.estimated_cost_usd.toFixed(6)}` : "—"}</div>
                </div>
                <div className="bg-muted/30 p-4 rounded-xl border flex flex-col gap-1">
                  <div className="text-xs text-muted-foreground flex items-center gap-1.5"><Database className="h-3 w-3"/> Memory</div>
                  <div className="font-medium">{selectedRuntime?.usage?.memory_mb !== undefined ? `${selectedRuntime.usage.memory_mb}MB` : "—"}</div>
                </div>
              </div>
            </div>

            {/* Events List */}
            <div className="space-y-3">
              <div className="text-xs font-semibold text-muted-foreground tracking-wider uppercase flex items-center gap-2">
                <ListTree className="h-3 w-3" /> Execution Events ({selectedRuntime?.events?.length || 0})
              </div>
              <div className="border rounded-xl overflow-hidden bg-background">
                <Table>
                  <TableHeader className="bg-muted/30">
                    <TableRow>
                      <TableHead className="w-[180px]">Timestamp</TableHead>
                      <TableHead>Event Type</TableHead>
                      <TableHead className="text-right">Payload Keys</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!selectedRuntime?.events || selectedRuntime.events.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={3} className="text-center text-muted-foreground py-6">No events recorded.</TableCell>
                      </TableRow>
                    ) : (
                      [...selectedRuntime.events]
                        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
                        .map((evt, idx) => {
                          const isExpanded = expandedEventIdx === idx;
                          return (
                            <React.Fragment key={`${evt.event_type}-${idx}`}>
                              <TableRow 
                                className="cursor-pointer hover:bg-muted/40 transition-colors"
                                onClick={() => setExpandedEventIdx(isExpanded ? null : idx)}
                              >
                                <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                                  <div className="flex items-center gap-2">
                                    {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                                    {new Date(evt.timestamp).toLocaleString()}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <Badge variant="secondary" className="bg-muted/50 font-mono text-xs">{evt.payload?.event_type}</Badge>
                                </TableCell>
                                <TableCell className="text-right text-xs text-muted-foreground font-mono">
                                  {evt.payload ? Object.keys(evt.payload).length : 0} keys
                                </TableCell>
                              </TableRow>
                              {isExpanded && evt.payload && (
                                <TableRow className="bg-muted/10 hover:bg-muted/10">
                                  <TableCell colSpan={3} className="p-0 border-b">
                                    <div className="p-4 overflow-x-auto max-h-[400px] overflow-y-auto">
                                      <pre className="text-xs text-foreground/80 font-mono whitespace-pre-wrap">{JSON.stringify(evt.payload, null, 2)}</pre>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              )}
                            </React.Fragment>
                          );
                        })
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>

            {/* Global Metadata */}
            {selectedRuntime?.metadata && Object.keys(selectedRuntime.metadata).length > 0 && (
              <div className="space-y-3">
                <div className="text-xs font-semibold text-muted-foreground tracking-wider uppercase flex items-center gap-2">
                  <SlidersHorizontal className="h-3 w-3" /> Global Metadata
                </div>
                <div className="bg-muted/30 rounded-lg p-4 font-mono text-xs overflow-x-auto border">
                  <pre className="text-foreground/80">{JSON.stringify(selectedRuntime.metadata, null, 2)}</pre>
                </div>
              </div>
            )}
            
            {(!selectedRuntime?.metadata && !selectedRuntime?.events?.length && !selectedRuntime?.usage) && (
              <div className="py-10 flex items-center justify-center text-muted-foreground text-sm border border-dashed rounded-xl bg-muted/10">
                No additional payload data available for this trace.
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
