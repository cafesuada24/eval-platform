"use client";

import React, { useState, useEffect } from "react";
import { Dataset, FileAsset } from "@/types/dataset";
import { fetchDatasetFiles } from "@/lib/api/datasets";
import { DatasetHeader } from "./DatasetHeader";
import { TestCaseList } from "./TestCaseList";
import { FileManager } from "./FileManager";
import { toast } from "sonner";
import { 
  ResizableHandle, 
  ResizablePanel, 
  ResizablePanelGroup 
} from "@/components/ui/resizable";

interface DatasetWorkspaceProps {
  dataset: Dataset;
}

export function DatasetWorkspace({ dataset }: DatasetWorkspaceProps) {
  const [files, setFiles] = useState<FileAsset[]>([]);

  useEffect(() => {
    fetchDatasetFiles(dataset.id)
      .then(setFiles)
      .catch(err => toast.error("Failed to fetch dataset files"));
  }, [dataset.id]);

  return (
    <div className="h-screen w-full flex flex-col bg-background text-foreground overflow-hidden">
      <DatasetHeader initialDataset={dataset} />
      
      <div className="flex-1 overflow-hidden">
        {/* @ts-ignore */}
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel defaultSize={62} minSize={40} className="bg-background">
            <div className="h-full overflow-y-auto px-8 pb-12">
              <TestCaseList dataset={dataset} files={files} />
            </div>
          </ResizablePanel>
          
          <ResizableHandle withHandle className="bg-muted" />
          
          {/* Sidebar (File Manager) - 38% default */}
          <ResizablePanel defaultSize={38} minSize={20} className="bg-background">
            <div className="h-full">
              <FileManager datasetId={dataset.id} files={files} setFiles={setFiles} />
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}
