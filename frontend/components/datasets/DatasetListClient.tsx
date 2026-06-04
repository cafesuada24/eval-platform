"use client"

import { Dataset } from "@/lib/types"
import { motion, Variants } from "framer-motion"
import Link from "next/link"
import { Database, ArrowUpRight, HardDrive } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface Props {
  datasets: Dataset[]
}

const container: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
}

const item: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
}

export function DatasetListClient({ datasets }: Props) {
  if (datasets.length === 0) {
    return (
      <div className="text-center p-16 border border-border/50 rounded-2xl bg-card/50 text-muted-foreground shadow-sm">
        <Database className="w-12 h-12 mx-auto mb-6 opacity-30" />
        <h3 className="text-xl font-medium text-foreground">No datasets found</h3>
        <p className="text-sm mt-2 font-mono">System awaiting initial data ingestion.</p>
      </div>
    )
  }

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      {datasets.map((dataset) => (
        <motion.div key={dataset.id} variants={item}>
          <Link href={`/datasets/${dataset.id}`}>
            <div className="group relative overflow-hidden rounded-2xl bg-card border border-border p-6 transition-all duration-300 hover:border-primary/50 hover:bg-card/80 active:scale-[0.98] shadow-sm">
              {/* Subtle radial glow on hover */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl" />
              
              <div className="relative z-10 flex flex-col h-full justify-between gap-8">
                <div className="flex items-start justify-between">
                  <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-background border border-border text-muted-foreground group-hover:text-primary transition-colors duration-300">
                    <HardDrive className="w-5 h-5" />
                  </div>
                  <ArrowUpRight className="w-5 h-5 text-muted-foreground opacity-0 -translate-x-2 translate-y-2 group-hover:opacity-100 group-hover:translate-x-0 group-hover:translate-y-0 transition-all duration-300 ease-out" />
                </div>
                
                <div className="space-y-3">
                  <h3 className="text-2xl font-bold tracking-tight text-foreground group-hover:text-primary transition-colors line-clamp-1">
                    {dataset.name}
                  </h3>
                  <div className="flex items-center gap-3">
                    <Badge variant="secondary" className="bg-secondary border-border text-secondary-foreground font-mono text-xs px-2.5 py-0.5">
                      {dataset.cases?.length || 0} CASES
                    </Badge>
                    <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest truncate max-w-[120px]">
                      {dataset.id.split('-')[0]}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </Link>
        </motion.div>
      ))}
    </motion.div>
  )
}
