import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2, Upload, Trash2, FileText, Eye, X } from "lucide-react";
import { toast } from "sonner";
import { getApiBaseUrl } from "@/lib/utils";

const API_BASE = getApiBaseUrl();

interface UploadedArtifact {
  id: string;
  name: string;
  text: string;
  size: number;
}

interface FileManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FileManagerModal({ isOpen, onClose }: FileManagerModalProps) {
  const [uploadedArtifacts, setUploadedArtifacts] = useState<UploadedArtifact[]>([]);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [previewFile, setPreviewFile] = useState<UploadedArtifact | null>(null);

  useEffect(() => {
    if (isOpen) {
      const fetchUploadedFiles = async () => {
        try {
          const res = await fetch(`${API_BASE}/v1/documents`);
          if (res.ok) {
            const files = await res.json();
            setUploadedArtifacts(files);
          } else {
            console.error("Failed to fetch uploaded files registry from backend");
          }
        } catch (err) {
          console.error("Error fetching uploaded files:", err);
        }
      };
      fetchUploadedFiles();
    }
  }, [isOpen]);

  const triggerNewFileUpload = () => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".txt,.md,.pdf,.png,.jpg,.jpeg,.webp,.json,.csv,.yaml,.yml";
    fileInput.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        setIsUploadingFile(true);
        try {
          const formData = new FormData();
          formData.append("file", file);
          
          const res = await fetch(`${API_BASE}/v1/documents/upload`, {
            method: "POST",
            body: formData
          });
          
          if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData?.detail || "Parsing failed");
          }
          
          const data: UploadedArtifact = await res.json();
          
          setUploadedArtifacts(prev => [...prev, data]);
          toast.success(`Successfully uploaded and parsed: ${data.name}`);
        } catch (err: unknown) {
          console.error(err);
          const msg = err instanceof Error ? err.message : 'Unknown error';
          toast.error(`Upload failed: ${msg}`);
        } finally {
          setIsUploadingFile(false);
        }
      }
    };
    fileInput.click();
  };

  const deleteArtifactFile = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/v1/documents/${id}`, {
        method: "DELETE"
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData?.detail || "Deletion failed");
      }

      setUploadedArtifacts(prev => prev.filter(file => file.id !== id));
      toast.success("File deleted from system repository.");
    } catch (err: unknown) {
      console.error(err);
      const msg = err instanceof Error ? err.message : 'Unknown error';
      toast.error(`Delete failed: ${msg}`);
    }
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col p-0 overflow-hidden">
          <DialogHeader className="p-6 border-b border-border/50 bg-muted/20 shrink-0">
            <DialogTitle className="flex items-center gap-2 text-xl">
              <FileText className="w-5 h-5 text-primary" />
              Manage Uploaded Files
            </DialogTitle>
            <DialogDescription>
              Upload and manage files. These files are vectorized into the RAG database and can be retrieved by the Agent.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider font-mono">
                System Repository
              </h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={triggerNewFileUpload}
                className="h-8 text-xs font-medium border-dashed px-3 flex items-center gap-1.5 hover:bg-primary/5 text-primary border-primary/30"
                disabled={isUploadingFile}
              >
                {isUploadingFile ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                <span>Upload New File</span>
              </Button>
            </div>

            <div className="space-y-2">
              {uploadedArtifacts.length === 0 ? (
                <div className="p-6 border border-dashed border-border/40 rounded-lg text-center bg-muted/15 flex flex-col items-center justify-center min-h-[160px]">
                  <Upload className="w-8 h-8 text-muted-foreground opacity-30 mb-2" />
                  <p className="text-sm text-foreground font-semibold">No files uploaded yet</p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-[250px] leading-relaxed">
                    Upload documents to persist them and provide context to your metrics.
                  </p>
                </div>
              ) : (
                uploadedArtifacts.map((file) => (
                  <div key={file.id} className="flex items-center justify-between p-3 rounded-lg border border-border/40 bg-background/40 hover:bg-background/80 transition-colors shadow-sm">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="p-2 bg-primary/10 rounded-md text-primary">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-foreground truncate leading-none mb-1.5">{file.name}</p>
                        <p className="text-[10px] text-muted-foreground font-mono">{(file.size / 1024).toFixed(1)} KB • OCR / Extracted Text</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => setPreviewFile(file)}
                        className="h-8 w-8 text-muted-foreground hover:text-foreground"
                        title="Preview Content"
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteArtifactFile(file.id)}
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        title="Delete File"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Preview Full-Screen Modal */}
      {previewFile && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl shadow-xl max-w-2xl w-full flex flex-col max-h-[85vh] overflow-hidden animate-in zoom-in-95 duration-150">
            <div className="px-6 py-4 border-b border-border/50 flex items-center justify-between shrink-0 bg-muted/30">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground truncate">{previewFile.name}</h3>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setPreviewFile(null)} className="h-7 w-7 rounded-full hover:bg-muted">
                <X className="w-4 h-4" />
              </Button>
            </div>
            <div className="p-6 overflow-y-auto flex-1 font-mono text-xs text-muted-foreground whitespace-pre-wrap bg-background/50 leading-relaxed max-h-[60vh]">
              {previewFile.text}
            </div>
            <div className="px-6 py-4 border-t border-border/50 flex justify-end shrink-0 bg-muted/10">
              <Button size="sm" onClick={() => setPreviewFile(null)}>Close Preview</Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
