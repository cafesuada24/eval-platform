"use client";

import React from "react";
import { FileAsset } from "@/types/dataset";
import { X, Copy, Download, Trash, AlertTriangle, FileText, Check } from "lucide-react";
import { getAbsoluteFileUrl } from "@/lib/utils";

interface FileViewerModalProps {
  file: FileAsset | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete?: (fileId: string) => Promise<void>;
}

export function FileViewerModal({ file, isOpen, onClose, onDelete }: FileViewerModalProps) {
  if (!isOpen || !file) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-card border border-border w-full max-w-5xl rounded-xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-muted/20">
          <div className="flex items-center space-x-3 min-w-0">
            <div className="p-2 bg-muted rounded-md text-muted-foreground flex-shrink-0">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-foreground truncate">{file.filename}</h3>
              <p className="text-xs text-muted-foreground font-mono truncate">{file.file_id}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>
        
        {/* Content Body */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-4 overflow-hidden">
          {/* Left Preview Pane */}
          <div className="md:col-span-3 p-6 bg-black/10 overflow-y-auto flex flex-col justify-center min-h-[350px]">
            <div className="text-center text-muted-foreground">Loading preview...</div>
          </div>
          
          {/* Right Sidebar Metadata */}
          <div className="p-6 border-t md:border-t-0 md:border-l border-border bg-muted/10 flex flex-col justify-between space-y-6">
            <div className="space-y-6">
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Asset Details</h4>
                <div className="space-y-3 text-sm">
                  <div>
                    <div className="text-xs text-muted-foreground">Ref Token</div>
                    <div className="font-mono text-primary bg-primary/5 p-1.5 rounded-md border border-primary/10 select-all mt-1 truncate">
                      {"{{"}file:{file.file_id}{"}}"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Absolute URL</div>
                    <div className="font-mono text-xs bg-muted p-1.5 rounded-md mt-1 truncate">
                      {getAbsoluteFileUrl(file.url)}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Actions</h4>
                <div className="space-y-2">
                  <a 
                    href={getAbsoluteFileUrl(file.url)} 
                    download={file.filename}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium border border-border bg-card hover:bg-muted text-foreground rounded-lg transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download File
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
