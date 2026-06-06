"use client"

import { Dataset } from "@/lib/types"
import { motion, Variants } from "framer-motion"
import { Box } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface Props {
  dataset: Dataset
}

const container: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05
    }
  }
}

const item: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
}

export function DatasetDetailClient({ dataset }: Props) {
  if (!dataset.cases || dataset.cases.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-24 border border-border/50 border-dashed rounded-3xl bg-card/30 text-muted-foreground">
        <Box className="w-16 h-16 mb-6 opacity-20" />
        <h3 className="text-xl font-medium text-foreground">Void</h3>
        <p className="text-sm mt-2 font-mono">No cases present in this dataset.</p>
      </div>
    )
  }

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="border border-border/80 rounded-xl overflow-hidden bg-background shadow-sm"
    >
      <Table>
        <TableHeader className="bg-muted/30">
          <TableRow className="border-border/80 hover:bg-transparent">
            <TableHead className="w-[120px] font-mono text-muted-foreground uppercase text-[10px] tracking-widest h-12">Case ID</TableHead>
            <TableHead className="font-mono text-muted-foreground uppercase text-[10px] tracking-widest h-12 w-1/3">Input Text</TableHead>
            <TableHead className="font-mono text-muted-foreground uppercase text-[10px] tracking-widest h-12 w-1/3">Expected Output</TableHead>
            <TableHead className="w-[200px] font-mono text-muted-foreground uppercase text-[10px] tracking-widest text-right h-12">Metadata</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {dataset.cases.map((testCase, idx) => (
            <motion.tr 
              key={testCase.id || idx}
              variants={item}
              className="group border-border/50 hover:bg-muted/30 transition-colors"
            >
              <TableCell className="align-top py-5">
                <span className="font-mono text-xs text-muted-foreground group-hover:text-primary transition-colors block truncate" title={testCase.id}>
                  {testCase.id ? testCase.id.split('-')[0] : `case-${idx+1}`}
                </span>
              </TableCell>
              <TableCell className="align-top py-5">
                <div className="font-mono text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed max-h-[160px] overflow-y-auto pr-2 space-y-1.5">
                  {Object.entries(testCase.inputs || {}).map(([key, val]) => (
                    <div key={key} className="flex flex-col gap-0.5">
                      <span className="text-[9px] font-semibold uppercase text-muted-foreground">{key}:</span>
                      <span className="text-foreground/90 break-all">{String(val)}</span>
                    </div>
                  ))}
                  {Object.keys(testCase.inputs || {}).length === 0 && (
                    <span className="text-muted-foreground italic">No inputs</span>
                  )}
                </div>
              </TableCell>
              <TableCell className="align-top py-5">
                <div className="font-mono text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed max-h-[160px] overflow-y-auto pr-2 space-y-1.5">
                  {Object.entries(testCase.expected_outputs || {}).map(([key, val]) => (
                    <div key={key} className="flex flex-col gap-0.5">
                      <span className="text-[9px] font-semibold uppercase text-muted-foreground">{key}:</span>
                      <span className="text-foreground/90 break-all">{String(val)}</span>
                    </div>
                  ))}
                  {Object.keys(testCase.expected_outputs || {}).length === 0 && (
                    <span className="text-muted-foreground italic">-</span>
                  )}
                </div>
              </TableCell>
              <TableCell className="align-top text-right py-5">
                {Object.keys(testCase.metadata || {}).length > 0 ? (
                  <div className="flex flex-col gap-1.5 items-end">
                    {Object.entries(testCase.metadata).map(([key, val]) => (
                      <div key={key} className="inline-flex items-center gap-1.5 bg-background border border-border rounded px-2 py-0.5 max-w-full">
                        <span className="text-[9px] font-mono uppercase text-muted-foreground">{key}:</span>
                        <span className="text-[10px] font-mono text-foreground/80 truncate max-w-[80px]" title={String(val)}>{String(val)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-muted-foreground italic text-xs font-mono">-</span>
                )}
              </TableCell>
            </motion.tr>
          ))}
        </TableBody>
      </Table>
    </motion.div>
  )
}
