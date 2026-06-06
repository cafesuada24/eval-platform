"use client";

import React, { useState, useRef, useEffect } from "react";
import { Dataset } from "@/types/dataset";
import { updateDataset } from "@/lib/api/datasets";
import { toast } from "sonner";
import { Play, Download } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DatasetHeaderProps {
  initialDataset: Dataset;
}

export function DatasetHeader({ initialDataset }: DatasetHeaderProps) {
  const [dataset, setDataset] = useState<Dataset>(initialDataset);
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(dataset.name);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleSave = async () => {
    setIsEditing(false);
    if (name.trim() === "" || name === dataset.name) {
      setName(dataset.name); // Revert to old if empty or unchanged
      return;
    }

    try {
      const updated = await updateDataset(dataset.id, name, dataset.schema);
      setDataset(updated);
      toast.success("Dataset name updated");
    } catch (error) {
      setName(dataset.name); // Revert on failure
      toast.error("Failed to update dataset name");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") {
      setName(dataset.name);
      setIsEditing(false);
    }
  };

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 py-8 px-8 bg-background border-b border-border">
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-primary uppercase tracking-widest mb-1">Dataset Builder</p>
        
        {isEditing ? (
          <input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleKeyDown}
            className="text-3xl font-bold bg-transparent text-foreground border-b-2 border-primary focus:outline-none w-full max-w-xl pb-1 rounded-[2px]"
          />
        ) : (
          <h1 
            onClick={() => setIsEditing(true)}
            className="text-3xl font-bold text-foreground cursor-pointer hover:text-primary transition-colors inline-block border-b-2 border-transparent hover:border-border/50 pb-1 rounded-[2px]"
            title="Click to edit name"
          >
            {dataset.name}
          </h1>
        )}
      </div>

      <div className="flex items-center gap-3">
        <Button variant="outline" className="border-border text-foreground hover:bg-muted hover:text-foreground rounded-[2px] font-mono text-[10px] uppercase tracking-wider h-9">
          <Download className="h-4 w-4 mr-2" /> Export
        </Button>
        <Button className="bg-primary text-primary-foreground hover:bg-primary/95 rounded-[2px] font-mono text-[10px] uppercase tracking-wider h-9 shadow-md shadow-primary/5">
          <Play className="h-4 w-4 mr-2" /> Run Evaluation
        </Button>
      </div>
    </div>
  );
}
