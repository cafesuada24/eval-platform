# Client-Side File Viewer Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to preview uploaded file assets (CSV, JSON, JSONL, Images, PDFs, media) in a centered modal overlay inside the EvalPlatform dashboard, with backend URL mismatches corrected.

**Architecture:** We will implement a custom Radix UI Dialog component (`FileViewerModal.tsx`) triggered by selecting a file in the `FileManager` sidebar. Text/data files will be fetched and parsed entirely on the client, truncating files above 1,000 lines/1MB to maintain smooth performance.

**Tech Stack:** Next.js 16 (App Router), React 19, Radix UI Dialog, Tailwind CSS, Lucide icons.

---

### Task 1: URL Normalizer Helper

**Files:**
- Modify: `frontend/lib/utils.ts`
- Create (Temporary): `frontend/lib/test-helper.ts`

- [ ] **Step 1: Write a temporary test script**
  Create `frontend/lib/test-helper.ts` containing unit test assertions for the URL resolution utility:
  ```typescript
  import { getAbsoluteFileUrl } from "./utils";

  function runTests() {
    console.log("Running URL Helper Tests...");
    
    // Test 1: Absolute URL passes through unmodified
    const url1 = "https://example.com/file.png";
    console.assert(getAbsoluteFileUrl(url1) === url1, `Test 1 Failed: Got ${getAbsoluteFileUrl(url1)}`);

    // Test 2: Mismatch /api/v1 prefix corrected and prefixed with localhost:8000
    const url2 = "/api/v1/datasets/d123/files/f_abc.csv";
    const expected2 = "http://localhost:8000/v1/datasets/d123/files/f_abc.csv";
    console.assert(getAbsoluteFileUrl(url2) === expected2, `Test 2 Failed: Got ${getAbsoluteFileUrl(url2)}`);

    // Test 3: Correct relative path prefixed
    const url3 = "/v1/datasets/d123/files/f_xyz.png";
    const expected3 = "http://localhost:8000/v1/datasets/d123/files/f_xyz.png";
    console.assert(getAbsoluteFileUrl(url3) === expected3, `Test 3 Failed: Got ${getAbsoluteFileUrl(url3)}`);

    console.log("All URL Helper Tests Passed!");
  }

  runTests();
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx tsx frontend/lib/test-helper.ts`
  Expected: FAIL with compilation error (getAbsoluteFileUrl not found/exported from utils).

- [ ] **Step 3: Implement getAbsoluteFileUrl in utils.ts**
  Add the implementation to `frontend/lib/utils.ts`:
  ```typescript
  export function getAbsoluteFileUrl(url?: string): string {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) {
      return url;
    }
    
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    let path = url;
    if (path.startsWith("/api/v1/")) {
      path = path.replace("/api/v1/", "/v1/");
    } else if (path.startsWith("api/v1/")) {
      path = "/" + path.replace("api/v1/", "v1/");
    }

    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    return `${apiBase}${cleanPath}`;
  }
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx tsx frontend/lib/test-helper.ts`
  Expected: PASS (All URL Helper Tests Passed!).

- [ ] **Step 5: Clean up and commit**
  Delete `frontend/lib/test-helper.ts`.
  Run:
  ```bash
  rm frontend/lib/test-helper.ts
  git add frontend/lib/utils.ts
  git commit -m "feat: add getAbsoluteFileUrl helper with API url normalizer"
  ```

---

### Task 2: File Viewer Modal Layout & UI Component

**Files:**
- Create: `frontend/components/datasets/FileViewerModal.tsx`

- [ ] **Step 1: Create the basic component structure**
  Create `frontend/components/datasets/FileViewerModal.tsx` with dialog framing using `@base-ui/react` or standard Radix Dialog:
  ```typescript
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
  ```

- [ ] **Step 2: Verify code compilation**
  Run build command to verify imports and types are clean:
  `npm run build`
  Expected: Successful compile (ignoring page router issues if any).

- [ ] **Step 3: Commit component stub**
  Run:
  ```bash
  git add frontend/components/datasets/FileViewerModal.tsx
  git commit -m "feat: create initial FileViewerModal structure"
  ```

---

### Task 3: Client-Side Parsers & Truncation

**Files:**
- Modify: `frontend/components/datasets/FileViewerModal.tsx`

- [ ] **Step 1: Implement CSV/JSONL parsing and preview states**
  Add state management to fetch the file contents when the modal opens and parse it. Replace the left preview pane logic with:
  ```typescript
  // Replace Left Preview Pane rendering & fetching logic inside FileViewerModal
  ```
  Here is the complete implementation of the parsing and UI inside `FileViewerModal.tsx`:
  ```typescript
  "use client";

  import React, { useState, useEffect } from "react";
  import { FileAsset } from "@/types/dataset";
  import { X, Copy, Download, Trash, AlertTriangle, FileText, Check, Loader2 } from "lucide-react";
  import { getAbsoluteFileUrl, formatDate } from "@/lib/utils";
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
    const [preview, setPreview] = useState<PreviewContent | null>(null);

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

    useEffect(() => {
      if (!isOpen || !file) {
        setPreview(null);
        return;
      }

      const absoluteUrl = getAbsoluteFileUrl(file.url);
      const ext = file.filename.split(".").pop()?.toLowerCase() || "";

      // Native preview types
      if (["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext)) {
        setPreview({ type: "image", url: absoluteUrl });
        return;
      }
      if (ext === "pdf") {
        setPreview({ type: "pdf", url: absoluteUrl });
        return;
      }
      if (["mp3", "wav", "ogg"].includes(ext)) {
        setPreview({ type: "media", url: absoluteUrl, isAudio: true });
        return;
      }
      if (["mp4", "webm"].includes(ext)) {
        setPreview({ type: "media", url: absoluteUrl, isAudio: false });
        return;
      }

      // Fetch and parse text-based formats
      if (["csv", "json", "jsonl", "txt", "md", "yaml", "yml"].includes(ext)) {
        setLoading(true);
        fetch(absoluteUrl)
          .then(async (res) => {
            if (!res.ok) throw new Error("Failed to load file contents");
            const text = await res.text();
            
            // Size check
            const limit = 1000;
            const lines = text.split("\n");
            const truncated = lines.length > limit;
            const contentLines = truncated ? lines.slice(0, limit) : lines;
            const cleanText = contentLines.join("\n");

            if (ext === "csv") {
              // Parse CSV lines
              const rows = contentLines.map(line => {
                // simple split by comma, respecting quotes
                const matches = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || line.split(",");
                return matches.map(cell => cell.replace(/^"|"$/g, "").trim());
              });
              const headers = rows[0] || [];
              const dataRows = rows.slice(1);
              setPreview({ type: "csv", headers, rows: dataRows, truncated });
            } else if (ext === "json") {
              try {
                const formatted = JSON.stringify(JSON.parse(text), null, 2);
                setPreview({ type: "json", text: formatted, truncated: false });
              } catch {
                setPreview({ type: "json", text: cleanText, truncated });
              }
            } else if (ext === "jsonl") {
              const formattedJsonl = contentLines.map((line, idx) => {
                if (!line.trim()) return "";
                try {
                  return JSON.stringify(JSON.parse(line));
                } catch {
                  return line;
                }
              }).join("\n");
              setPreview({ type: "json", text: formattedJsonl, truncated });
            } else {
              setPreview({ type: "text", text: cleanText, truncated });
            }
          })
          .catch((err) => {
            console.error(err);
            setPreview({ type: "fallback", url: absoluteUrl });
          })
          .finally(() => setLoading(false));
        return;
      }

      // Fallback
      setPreview({ type: "fallback", url: absoluteUrl });
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
                      <span>Large File: Displaying the first 1,000 lines. Please download the complete file to view everything.</span>
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
                        <button onClick={handleCopyRef} className="p-1.5 border border-border rounded-md hover:bg-muted text-muted-foreground hover:text-foreground">
                          {copiedRef ? <Check className="h-4 w-4 text-primary" /> : <Copy className="h-4 w-4" />}
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
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium border border-border bg-card hover:bg-muted text-foreground rounded-lg transition-colors"
                    >
                      {copiedUrl ? <Check className="h-3.5 w-3.5 text-primary" /> : <Copy className="h-3.5 w-3.5" />}
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
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/20 rounded-lg transition-colors"
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
  ```

- [ ] **Step 2: Verify code compiles**
  Run: `npm run build`
  Expected: Successful compilation of FileViewerModal component.

- [ ] **Step 3: Commit code**
  Run:
  ```bash
  git add frontend/components/datasets/FileViewerModal.tsx
  git commit -m "feat: implement CSV, JSON, PDF and image preview parsers in FileViewerModal"
  ```

---

### Task 4: Hook File Viewer Modal into FileManager

**Files:**
- Modify: `frontend/components/datasets/FileManager.tsx`

- [ ] **Step 1: Check imports and register Delete function**
  Ensure standard imports and correct state hookups in `frontend/components/datasets/FileManager.tsx`:
  ```typescript
  import { FileViewerModal } from "./FileViewerModal";
  import { getAbsoluteFileUrl } from "@/lib/utils";
  ```

- [ ] **Step 2: Add Active File State & Delete Action**
  Implement active state inside `FileManager` class component/function:
  ```typescript
  const [activeFile, setActiveFile] = useState<FileAsset | null>(null);
  ```
  Add a delete handler matching backend endpoints:
  ```typescript
  const handleDeleteFile = async (fileId: string) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/v1/datasets/${datasetId}/files/${fileId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete file");
      setFiles(prev => prev.filter(f => f.file_id !== fileId));
      toast.success("File deleted successfully");
    } catch (error) {
      toast.error("Failed to delete file");
    }
  };
  ```

- [ ] **Step 3: Update thumbnail and details to use absolute URLs**
  Update line `124` to `132` in `FileManager.tsx`:
  ```diff
  - {file.url && /\.(jpe?g|png|gif|webp|svg)$/i.test(file.filename) ? (
  -   <div className="h-8 w-8 flex-shrink-0 rounded-md overflow-hidden bg-muted flex items-center justify-center">
  -     <img src={file.url} alt={file.filename} className="object-cover h-full w-full" />
  -   </div>
  - ) : (
  + {file.url && /\.(jpe?g|png|gif|webp|svg)$/i.test(file.filename) ? (
  +   <div className="h-8 w-8 flex-shrink-0 rounded-md overflow-hidden bg-muted flex items-center justify-center">
  +     <img src={getAbsoluteFileUrl(file.url)} alt={file.filename} className="object-cover h-full w-full" />
  +   </div>
  + ) : (
  ```
  Update line `139` to `163` (the actions and open-in-new-tab anchor links):
  ```diff
  - <Button
  -   variant="ghost"
  -   size="icon"
  -   onClick={() => window.open(file.url, '_blank')}
  -   className="flex-shrink-0 text-muted-foreground hover:text-foreground"
  -   title="Open File URL"
  - >
  + <Button
  +   variant="ghost"
  +   size="icon"
  +   onClick={() => window.open(getAbsoluteFileUrl(file.url), '_blank')}
  +   className="flex-shrink-0 text-muted-foreground hover:text-foreground"
  +   title="Open File URL"
  + >
  ```

- [ ] **Step 4: Update the file card click to open FileViewerModal**
  Wrap the file asset wrapper click so that clicking the title/card triggers the modal:
  ```diff
  - <div key={file.file_id} className="flex items-center justify-between p-3 bg-card rounded-lg border border-border group hover:border-border transition-colors">
  + <div 
  +   key={file.file_id} 
  +   onClick={() => setActiveFile(file)}
  +   className="flex items-center justify-between p-3 bg-card rounded-lg border border-border group hover:border-border hover:bg-muted/10 transition-colors cursor-pointer"
  + >
  ```
  Wait, clicking on the action buttons shouldn't trigger the modal click. Stop propagation on the buttons:
  ```diff
    <div className="flex items-center space-x-1" onClick={(e) => e.stopPropagation()}>
  ```
  Add the modal at the bottom of the component:
  ```typescript
    <FileViewerModal 
      file={activeFile} 
      isOpen={activeFile !== null} 
      onClose={() => setActiveFile(null)} 
      onDelete={handleDeleteFile}
    />
  ```

- [ ] **Step 5: Verify build compile**
  Run: `npm run build`
  Expected: Successful compilation of all components.

- [ ] **Step 6: Commit code**
  Run:
  ```bash
  git add frontend/components/datasets/FileManager.tsx
  git commit -m "feat: hook FileViewerModal and absolute url resolution into FileManager"
  ```

---

### Task 5: Verification and Manual E2E Checks

- [ ] **Step 1: Run local development environment**
  Verify the server and dashboard starts up without any issues.
  Command: `npm run dev` in `frontend` folder.

- [ ] **Step 2: Inspect file upload and click**
  Navigate to a dataset workspace page, upload a sample CSV or image, and verify:
  1. Image thumbnails are displayed (proving url resolution is working correctly).
  2. Clicking the file card opens the Dialog overlay modal.
  3. Previews load for CSV/JSON formats.
  4. Deletion works and removes the file from the list.
