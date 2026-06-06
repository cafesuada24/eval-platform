"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, File as FileIcon, Copy, Loader2, Check } from "lucide-react";
import { uploadFile } from "@/lib/api/datasets";
import { FileAsset } from "@/types/dataset";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

interface FileManagerProps {
  datasetId: string;
  files: FileAsset[];
  setFiles: React.Dispatch<React.SetStateAction<FileAsset[]>>;
}

export function FileManager({ datasetId, files, setFiles }: FileManagerProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleUpload(e.target.files[0]);
    }
  };

  const handleUpload = async (file: File) => {
    try {
      setIsUploading(true);
      const newFile = await uploadFile(datasetId, file);
      setFiles(prev => [newFile, ...prev]);
      toast.success("File uploaded successfully");
    } catch (error) {
      toast.error("Failed to upload file");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = ""; // Reset input
    }
  };

  const copyToClipboard = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    toast.success("File ID copied to clipboard");
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-background border-l border-border">
      <div className="p-6 border-b border-border bg-card/50">
        <h3 className="text-lg font-semibold text-foreground mb-1">File Assets</h3>
        <p className="text-sm text-muted-foreground mb-6">Upload images or documents to reference in your test cases.</p>
        
        <div 
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
            isDragging 
              ? "border-primary bg-primary/10" 
              : "border-border bg-card hover:border-primary/50 hover:bg-muted"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileInput} 
            className="hidden" 
          />
          
          {isUploading ? (
            <div className="flex flex-col items-center justify-center space-y-3">
              <Loader2 className="h-8 w-8 text-primary animate-spin" />
              <p className="text-sm font-medium text-primary">Uploading...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="p-3 bg-muted rounded-full">
                <UploadCloud className="h-6 w-6 text-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Click to upload or drag and drop</p>
                <p className="text-xs text-muted-foreground mt-1">Images, Audio, PDF, etc.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Uploaded Files ({files.length})
        </h4>
        
        {files.length === 0 ? (
          <div className="text-sm text-muted-foreground italic text-center py-8">
            No files uploaded yet.
          </div>
        ) : (
          files.map((file) => (
            <div key={file.file_id} className="flex items-center justify-between p-3 bg-card rounded-lg border border-border group hover:border-border transition-colors">
              <div className="flex items-center space-x-3 overflow-hidden">
                {file.url && /\.(jpe?g|png|gif|webp|svg)$/i.test(file.filename) ? (
                  <div className="h-8 w-8 flex-shrink-0 rounded-md overflow-hidden bg-muted flex items-center justify-center">
                    <img src={file.url} alt={file.filename} className="object-cover h-full w-full" />
                  </div>
                ) : (
                  <div className="p-2 bg-muted rounded-md text-muted-foreground flex-shrink-0">
                    <FileIcon className="h-4 w-4" />
                  </div>
                )}
                <div className="overflow-hidden">
                  <p className="text-sm font-medium text-foreground truncate">{file.filename}</p>
                  <p className="text-xs text-muted-foreground font-mono truncate">{file.file_id}</p>
                </div>
              </div>
              <div className="flex items-center space-x-1">
                {file.url && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => window.open(file.url, '_blank')}
                    className="flex-shrink-0 text-muted-foreground hover:text-foreground"
                    title="Open File URL"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                      <polyline points="15 3 21 3 21 9"></polyline>
                      <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => copyToClipboard(file.file_id)}
                  className={`flex-shrink-0 ${copiedId === file.file_id ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}
                  title="Copy File ID"
                >
                  {copiedId === file.file_id ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
