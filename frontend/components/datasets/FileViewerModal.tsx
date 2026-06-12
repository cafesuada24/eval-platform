"use client";

import React, { useState, useEffect } from "react";
import { FileAsset } from "@/types/dataset";
import { X, Copy, Download, Trash, AlertTriangle, FileText, Check, Loader2 } from "lucide-react";
import { getAbsoluteFileUrl } from "@/lib/utils";
import { toast } from "sonner";

interface FileViewerModalProps {
  file: FileAsset | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete?: (fileId: string) => Promise<void>;
}

type PreviewContent = 
  | { type: "image"; url: string }
  | { type: "pdf"; url: string }
  | { type: "media"; url: string; isAudio: boolean }
  | { type: "csv"; headers: string[]; rows: string[][]; truncated: boolean }
  | { type: "json" | "text"; text: string; truncated: boolean }
  | { type: "fallback"; url: string };

export function FileViewerModal({ file, isOpen, onClose, onDelete }: FileViewerModalProps) {
  const [loading, setLoading] = useState(false);
  const [copiedRef, setCopiedRef] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [asyncPreview, setAsyncPreview] = useState<PreviewContent | null>(null);

  const handleCopyRef = () => {
    if (!file) return;
    navigator.clipboard.writeText(`{{file:${file.file_id}}}`);
    setCopiedRef(true);
    toast.success("Reference token copied");
    setTimeout(() => setCopiedRef(false), 2000);
  };

  const handleCopyUrl = () => {
    if (!file) return;
    navigator.clipboard.writeText(getAbsoluteFileUrl(file.url));
    setCopiedUrl(true);
    toast.success("File URL copied");
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  const absoluteUrl = file ? getAbsoluteFileUrl(file.url) : "";
  const ext = file ? file.filename.split(".").pop()?.toLowerCase() || "" : "";

  // Compute preview type during render if possible to avoid synchronous setState inside useEffect
  let preview: PreviewContent | null = null;
  if (file) {
    if (["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext)) {
      preview = { type: "image", url: absoluteUrl };
    } else if (ext === "pdf") {
      preview = { type: "pdf", url: absoluteUrl };
    } else if (["mp3", "wav", "ogg"].includes(ext)) {
      preview = { type: "media", url: absoluteUrl, isAudio: true };
    } else if (["mp4", "webm"].includes(ext)) {
      preview = { type: "media", url: absoluteUrl, isAudio: false };
    } else {
      preview = asyncPreview;
    }
  }

  useEffect(() => {
    if (!isOpen || !file) return;

    const currentAbsoluteUrl = getAbsoluteFileUrl(file.url);
    const currentExt = file.filename.split(".").pop()?.toLowerCase() || "";

    // If it is not a text format, we don't need to fetch
    if (!["csv", "json", "jsonl", "txt", "md", "yaml", "yml"].includes(currentExt)) {
      return;
    }

    let active = true;
    setTimeout(() => {
      if (active) {
        setLoading(true);
      }
    }, 0);
    fetch(currentAbsoluteUrl)
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to load file contents");
        
        const contentLengthHeader = res.headers.get("content-length");
        const contentLength = contentLengthHeader ? parseInt(contentLengthHeader, 10) : 0;
        
        const text = await res.text();
        if (!active) return;

        const byteSize = new Blob([text]).size;
        const sizeLimit = 2 * 1024 * 1024; // 2MB limit
        const lineLimit = 1000;
        const lines = text.split("\n");
        
        const isTooLarge = byteSize > sizeLimit || contentLength > sizeLimit;
        const isTooManyLines = lines.length > lineLimit;
        const truncated = isTooLarge || isTooManyLines;
        
        const contentLines = truncated ? lines.slice(0, lineLimit) : lines;
        const cleanText = contentLines.join("\n");

        if (currentExt === "csv") {
          // Parse CSV lines respecting quotes and commas
          const rows = contentLines.map(line => {
            const matches = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || line.split(",");
            return matches.map(cell => cell.replace(/^"|"$/g, "").trim());
          });
          const headers = rows[0] || [];
          const dataRows = rows.slice(1);
          setAsyncPreview({ type: "csv", headers, rows: dataRows, truncated });
        } else if (currentExt === "json") {
          try {
            const formatted = JSON.stringify(JSON.parse(text), null, 2);
            const formattedLines = formatted.split("\n");
            if (formattedLines.length > lineLimit) {
              setAsyncPreview({
                type: "json",
                text: formattedLines.slice(0, lineLimit).join("\n"),
                truncated: true
              });
            } else {
              setAsyncPreview({ type: "json", text: formatted, truncated });
            }
          } catch {
            setAsyncPreview({ type: "json", text: cleanText, truncated });
          }
        } else if (currentExt === "jsonl") {
          const formattedJsonl = contentLines.map((line) => {
            if (!line.trim()) return "";
            try {
              return JSON.stringify(JSON.parse(line));
            } catch {
              return line;
            }
          }).join("\n");
          setAsyncPreview({ type: "json", text: formattedJsonl, truncated });
        } else {
          setAsyncPreview({ type: "text", text: cleanText, truncated });
        }
      })
      .catch((err) => {
        console.error(err);
        if (active) {
          setAsyncPreview({ type: "fallback", url: currentAbsoluteUrl });
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
      setAsyncPreview(null);
    };
  }, [file, isOpen]);

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
          <div className="md:col-span-3 p-6 bg-black/10 overflow-y-auto flex flex-col min-h-[350px]">
            {loading ? (
              <div className="flex flex-col items-center justify-center flex-1 space-y-3">
                <Loader2 className="h-8 w-8 text-primary animate-spin" />
                <p className="text-sm text-muted-foreground">Fetching file content...</p>
              </div>
            ) : preview ? (
              <div className="flex-1 flex flex-col">
                {/* Truncation warning banner */}
                {("truncated" in preview && preview.truncated) && (
                  <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-500 px-3 py-2.5 rounded-lg text-xs mb-4">
                    <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                    <span>Large File (over 2MB or 1,000 lines): Displaying the first 1,000 lines. Please download the complete file to view everything.</span>
                  </div>
                )}

                {preview.type === "image" && (
                  <div className="flex-1 flex items-center justify-center">
                    <img src={preview.url} alt={file.filename} className="max-h-[60vh] max-w-full object-contain rounded-md border border-border bg-card" />
                  </div>
                )}

                {preview.type === "pdf" && (
                  <iframe src={preview.url} className="flex-1 w-full min-h-[55vh] rounded-md border border-border" />
                )}

                {preview.type === "media" && (
                  <div className="flex-1 flex items-center justify-center p-8 bg-card rounded-md border border-border">
                    {preview.isAudio ? (
                      <audio src={preview.url} controls className="w-full max-w-md" />
                    ) : (
                      <video src={preview.url} controls className="max-h-[50vh] max-w-full rounded-md" />
                    )}
                  </div>
                )}

                {preview.type === "csv" && (
                  <div className="flex-1 border border-border rounded-lg overflow-x-auto bg-card">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-muted border-b border-border">
                          {preview.headers.map((h, i) => (
                            <th key={i} className="p-2.5 font-semibold text-muted-foreground">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {preview.rows.map((row, rIdx) => (
                          <tr key={rIdx} className="border-b border-border last:border-0 hover:bg-muted/30">
                            {row.map((cell, cIdx) => (
                              <td key={cIdx} className="p-2.5 font-mono text-foreground">{cell}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {preview.type === "json" && (
                  <pre className="flex-1 bg-card border border-border p-4 rounded-lg overflow-auto font-mono text-xs text-foreground whitespace-pre-wrap">
                    {preview.text}
                  </pre>
                )}

                {preview.type === "text" && (
                  <pre className="flex-1 bg-card border border-border p-4 rounded-lg overflow-auto font-mono text-xs text-foreground whitespace-pre">
                    {preview.text}
                  </pre>
                )}

                {preview.type === "fallback" && (
                  <div className="flex-1 flex flex-col items-center justify-center text-center space-y-4">
                    <FileText className="h-16 w-16 text-muted-foreground stroke-1" />
                    <div>
                      <h4 className="font-semibold text-foreground">Preview Not Available</h4>
                      <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                        This file type cannot be previewed in the browser. You can download it directly instead.
                      </p>
                    </div>
                    <a 
                      href={preview.url} 
                      download={file.filename}
                      className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition-colors"
                    >
                      <Download className="h-4 w-4" />
                      Download Full File
                    </a>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-muted-foreground flex-1 flex items-center justify-center">No preview source loaded.</div>
            )}
          </div>
          
          {/* Right Sidebar Metadata */}
          <div className="p-6 border-t md:border-t-0 md:border-l border-border bg-muted/10 flex flex-col justify-between space-y-6">
            <div className="space-y-6">
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Asset Details</h4>
                <div className="space-y-3 text-sm">
                  <div>
                    <div className="text-xs text-muted-foreground">Reference Token</div>
                    <div className="flex gap-1.5 mt-1">
                      <div className="font-mono text-xs text-primary bg-primary/5 p-1.5 rounded-md border border-primary/10 select-all truncate flex-1">
                        {"{{"}file:{file.file_id}{"}}"}
                      </div>
                      <button onClick={handleCopyRef} className="p-1.5 border border-border rounded-md hover:bg-muted text-muted-foreground hover:text-foreground cursor-pointer">
                        {copiedRef ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Source Name</div>
                    <div className="font-semibold text-foreground mt-0.5 truncate">{file.filename}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">File ID</div>
                    <div className="font-mono text-xs text-foreground mt-0.5 truncate">{file.file_id}</div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Actions</h4>
                <div className="space-y-2">
                  <button 
                    onClick={handleCopyUrl}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium border border-border bg-card hover:bg-muted text-foreground rounded-lg transition-colors cursor-pointer"
                  >
                    {copiedUrl ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
                    Copy File URL
                  </button>
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

            {onDelete && (
              <div>
                <button 
                  onClick={() => {
                    if (confirm(`Are you sure you want to delete "${file.filename}"?`)) {
                      onDelete(file.file_id);
                      onClose();
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/20 rounded-lg transition-colors cursor-pointer"
                >
                  <Trash className="h-3.5 w-3.5" />
                  Delete Asset
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
