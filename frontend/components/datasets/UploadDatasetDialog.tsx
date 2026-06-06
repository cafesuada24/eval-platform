"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Upload, AlertCircle } from "lucide-react"
import { toast } from "sonner"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function UploadDatasetDialog() {
  const [open, setOpen] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const router = useRouter()

  const validateFile = async (f: File): Promise<boolean> => {
    try {
      const text = await f.text()
      if (f.name.endsWith('.json')) {
        const data = JSON.parse(text)
        // Check if data is array
        const items = Array.isArray(data) ? data : (data.items || data.cases || [data])
        if (!Array.isArray(items) || items.length === 0) {
          setErrorMsg("JSON must be an array of test cases.")
          return false
        }
        
        // Check first item for inputs.query
        const first = items[0]
        if (!first.inputs || typeof first.inputs !== 'object' || !('query' in first.inputs)) {
          setErrorMsg("Invalid Schema: Test cases must contain an 'inputs' object with a 'query' field.")
          return false
        }
        return true
      } else if (f.name.endsWith('.csv')) {
        const firstLine = text.split('\n')[0].toLowerCase()
        const headers = firstLine.split(',').map(h => h.trim().replace(/^"|"$/g, ''))
        if (!headers.includes('query')) {
          setErrorMsg("Invalid Schema: CSV must contain a 'query' column.")
          return false
        }
        return true
      }
      return true // Unknown type, let backend handle
    } catch (e) {
      setErrorMsg("Failed to parse file. Ensure it is valid JSON or CSV.")
      return false
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null)
    const selected = e.target.files?.[0] || null
    setFile(selected)
    
    if (selected) {
      await validateFile(selected)
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || errorMsg) return

    setIsUploading(true)
    const formData = new FormData()
    formData.append("file", file)

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const res = await fetch(`${API_BASE_URL}/v1/datasets/upload`, {
        method: "POST",
        body: formData,
      })

      if (!res.ok) {
        throw new Error("Failed to upload dataset")
      }

      toast.success("Dataset uploaded successfully")
      setOpen(false)
      setFile(null)
      router.refresh()
    } catch (error) {
      toast.error("Error uploading dataset. Make sure it matches the strict schema.")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if(!o) { setFile(null); setErrorMsg(null); } }}>
      <DialogTrigger className={cn(buttonVariants({ variant: "default" }), "bg-primary text-primary-foreground hover:bg-primary")}>
        <Upload className="w-4 h-4 mr-2" />
        Upload Dataset
      </DialogTrigger>
      <DialogContent className="sm:max-w-md border-border bg-background text-foreground">
        <DialogHeader>
          <DialogTitle>Upload Dataset</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Upload a JSON or CSV file containing your test cases.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleUpload} className="space-y-4 pt-4">
          <div className="grid w-full items-center gap-1.5">
            <Input 
              id="dataset" 
              type="file" 
              accept=".json,.csv"
              onChange={handleFileChange}
              className="cursor-pointer file:cursor-pointer bg-card border-border focus-visible:ring-ring"
            />
          </div>
          
          {errorMsg && (
            <div className="flex items-start gap-2 p-3 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-md">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <p>{errorMsg}</p>
            </div>
          )}

          <div className="flex justify-end gap-3 mt-6">
            <Button variant="outline" type="button" onClick={() => setOpen(false)} className="border-border text-foreground hover:bg-muted">
              Cancel
            </Button>
            <Button type="submit" disabled={!file || !!errorMsg || isUploading} className="bg-primary hover:bg-primary text-primary-foreground">
              {isUploading ? "Uploading..." : "Upload"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
