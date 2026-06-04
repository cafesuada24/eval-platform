"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Upload } from "lucide-react"
import { toast } from "sonner"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function UploadDatasetDialog() {
  const [open, setOpen] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const router = useRouter()

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setIsUploading(true)
    const formData = new FormData()
    formData.append("file", file)

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const res = await fetch(`${API_BASE_URL}/v1/datasets/`, {
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
      toast.error("Error uploading dataset. Make sure it's a valid JSON or CSV.")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className={cn(buttonVariants({ variant: "default" }), "bg-primary text-primary-foreground hover:bg-primary/90")}>
        <Upload className="w-4 h-4 mr-2" />
        Upload Dataset
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Dataset</DialogTitle>
          <DialogDescription>
            Upload a JSON or CSV file containing your test cases.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleUpload} className="space-y-4 pt-4">
          <div className="grid w-full items-center gap-1.5">
            <Input 
              id="dataset" 
              type="file" 
              accept=".json,.csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="cursor-pointer file:cursor-pointer"
            />
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <Button variant="outline" type="button" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!file || isUploading}>
              {isUploading ? "Uploading..." : "Upload"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
