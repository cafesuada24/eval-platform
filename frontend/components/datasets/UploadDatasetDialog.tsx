"use client"

import { useState, useRef } from "react"
import { useRouter } from "next/navigation"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Upload, AlertCircle, CheckCircle2, ChevronRight, Info, FileJson, FileSpreadsheet, Settings2, Eye, EyeOff } from "lucide-react"
import { toast } from "sonner"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { motion, AnimatePresence } from "framer-motion"

// --- Helper Types & Helpers ---

type Step = 'select' | 'mapping' | 'uploading' | 'success' | 'error'

interface PreviewResult {
  columns: string[]
  rows: Record<string, any>[]
}

const flattenKeys = (obj: any, prefix = ""): Record<string, any> => {
  const result: Record<string, any> = {}
  if (!obj || typeof obj !== 'object') return result

  for (const [key, value] of Object.entries(obj)) {
    const propName = prefix ? `${prefix}${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value) && key !== 'metadata') {
      Object.assign(result, flattenKeys(value, `${propName}.`))
    } else {
      result[propName] = value
    }
  }
  return result
}

// Partial read parsers to avoid loading huge files into memory for preview
const readCsvPreview = async (f: File): Promise<PreviewResult> => {
  const blob = f.slice(0, 50 * 1024) // Read first 50KB
  const text = await blob.text()
  const lines = text.split('\n')
  if (lines.length === 0) return { columns: [], rows: [] }

  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  const rows: any[] = []

  for (let i = 1; i < Math.min(lines.length, 6); i++) {
    const line = lines[i].trim()
    if (!line) continue
    const values = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))
    const row: any = {}
    headers.forEach((h, index) => {
      row[h] = values[index] || ''
    })
    rows.push(row)
  }
  return { columns: headers, rows }
}

const readJsonPreview = async (f: File): Promise<PreviewResult> => {
  if (f.size < 5 * 1024 * 1024) {
    const text = await f.text()
    const data = JSON.parse(text)
    const items = Array.isArray(data) ? data : (data.items || data.cases || [data])
    if (!Array.isArray(items) || items.length === 0) return { columns: [], rows: [] }

    const previewRows = items.slice(0, 5).map(item => flattenKeys(item))
    const allKeys = Array.from(new Set(previewRows.flatMap(r => Object.keys(r))))
    return { columns: allKeys, rows: previewRows }
  } else {
    // Large JSON files: grab first 100KB and try parsing first few objects
    const blob = f.slice(0, 100 * 1024)
    const text = await blob.text()
    const regex = /\{[^{}]*\}/g
    const matches = text.match(regex)
    if (!matches || matches.length === 0) {
      return { columns: [], rows: [] }
    }
    const rows = matches.slice(0, 5).map(m => {
      try {
        return flattenKeys(JSON.parse(m))
      } catch {
        return {}
      }
    }).filter(r => Object.keys(r).length > 0)
    const allKeys = Array.from(new Set(rows.flatMap(r => Object.keys(r))))
    return { columns: allKeys, rows }
  }
}

const readJsonlPreview = async (f: File): Promise<PreviewResult> => {
  const blob = f.slice(0, 50 * 1024)
  const text = await blob.text()
  const lines = text.split('\n')
  const rows: any[] = []

  for (let i = 0; i < Math.min(lines.length, 5); i++) {
    const line = lines[i].trim()
    if (!line) continue
    try {
      rows.push(flattenKeys(JSON.parse(line)))
    } catch {
      // Skip invalid preview rows
    }
  }
  const allKeys = Array.from(new Set(rows.flatMap(r => Object.keys(r))))
  return { columns: allKeys, rows }
}

const getAutoMapping = (columns: string[]): Record<string, string> => {
  const mapping: Record<string, string> = {}
  const querySynonyms = ['query', 'prompt', 'question', 'input', 'input_text', 'user_input', 'inputs.query']
  const outputSynonyms = ['expected_output', 'answer', 'ground_truth', 'reference', 'expected', 'gold', 'outputs.expected_output', 'outputs.output', 'expected_outputs.expected_output']

  columns.forEach(col => {
    const lower = col.toLowerCase()
    if (querySynonyms.includes(lower) || lower.endsWith('.query')) {
      mapping[col] = 'query'
    } else if (outputSynonyms.includes(lower) || lower.endsWith('.expected_output') || lower.endsWith('.output')) {
      mapping[col] = 'expected_output'
    } else if (lower.startsWith('metadata.')) {
      mapping[col] = col
    } else if (['tags', 'category', 'label', 'context'].includes(lower)) {
      mapping[col] = `metadata.${col}`
    } else {
      // Auto-assign as extra input variable
      mapping[col] = `inputs.${col}`
    }
  })

  return mapping
}

export function UploadDatasetDialog() {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<Step>('select')
  const [file, setFile] = useState<File | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [warningMsg, setWarningMsg] = useState<string | null>(null)
  
  const [columns, setColumns] = useState<string[] | null>(null)
  const [previewRows, setPreviewRows] = useState<Record<string, any>[] | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [showDataPreview, setShowDataPreview] = useState(false)

  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)

  const [datasetName, setDatasetName] = useState("")
  const [datasetDescription, setDatasetDescription] = useState("")

  const fileInputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()

  const resetState = () => {
    setFile(null)
    setStep('select')
    setErrorMsg(null)
    setWarningMsg(null)
    setColumns(null)
    setPreviewRows(null)
    setMapping({})
    setUploadProgress(0)
    setIsUploading(false)
    setShowDataPreview(false)
    setDatasetName("")
    setDatasetDescription("")
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null)
    setWarningMsg(null)
    const selected = e.target.files?.[0] || null
    if (!selected) return

    setFile(selected)

    // Evaluate file size warnings (50MB warning, 200MB caution)
    if (selected.size > 200 * 1024 * 1024) {
      setWarningMsg("Very large file (200MB+). Consider splitting into smaller datasets to prevent browser timeouts.")
    } else if (selected.size > 50 * 1024 * 1024) {
      setWarningMsg("Large file (50MB+) detected. The upload might take a few moments.")
    }

    try {
      let result: PreviewResult
      if (selected.name.endsWith('.json')) {
        result = await readJsonPreview(selected)
      } else if (selected.name.endsWith('.jsonl')) {
        result = await readJsonlPreview(selected)
      } else if (selected.name.endsWith('.csv')) {
        result = await readCsvPreview(selected)
      } else {
        setErrorMsg("Unsupported file format. Please upload JSON, JSONL, or CSV.")
        return
      }

      if (result.columns.length === 0) {
        setErrorMsg("Could not detect any columns/keys in the file. Ensure it is a valid CSV, JSON array, or JSONL.")
        return
      }

      setColumns(result.columns)
      setPreviewRows(result.rows)
      setMapping(getAutoMapping(result.columns))
    } catch (err: any) {
      setErrorMsg(`Failed to analyze file: ${err.message || 'unknown error'}`)
    }
  }

  const handleMappingChange = (col: string, value: string) => {
    setMapping(prev => ({ ...prev, [col]: value }))
  }

  // Map checking for query field
  const isQueryMapped = Object.values(mapping).some(v => v === 'query')

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !isQueryMapped || isUploading) return

    setIsUploading(true)
    setStep('uploading')

    const formData = new FormData()
    formData.append("file", file)
    
    // Filter excluded keys and construct clean column mapping
    const cleanMapping: Record<string, string> = {}
    Object.entries(mapping).forEach(([k, v]) => {
      if (v !== 'exclude') {
        cleanMapping[k] = v
      }
    })
    formData.append("column_mapping", JSON.stringify(cleanMapping))
    if (datasetName.trim()) formData.append("name", datasetName.trim())
    if (datasetDescription.trim()) formData.append("description", datasetDescription.trim())

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      
      // XMLHTTPRequest to monitor upload progress
      const xhr = new XMLHttpRequest()
      xhr.open("POST", `${API_BASE_URL}/v1/datasets/upload`, true)

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100)
          setUploadProgress(percent)
        }
      }

      const uploadPromise = new Promise((resolve, reject) => {
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText))
          } else {
            try {
              const errorRes = JSON.parse(xhr.responseText)
              reject(new Error(errorRes.detail || "Upload failed"))
            } catch {
              reject(new Error(`Upload failed with status code ${xhr.status}`))
            }
          }
        }
        xhr.onerror = () => reject(new Error("Network error during upload"))
      })

      xhr.send(formData)
      await uploadPromise

      setStep('success')
      toast.success("Dataset uploaded successfully")
      router.refresh()
    } catch (error: any) {
      setErrorMsg(error.message || "Failed to upload dataset. Check schema structure.")
      setStep('error')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if(!o) resetState(); }}>
      <DialogTrigger className={cn(buttonVariants({ variant: "default" }), "bg-primary text-primary-foreground hover:bg-primary/90 transition-all font-medium flex items-center")}>
        <Upload className="w-4 h-4 mr-2" />
        Upload Dataset
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-2xl md:max-w-3xl lg:max-w-4xl border-border bg-background text-foreground overflow-hidden max-h-[85vh] flex flex-col p-6 shadow-2xl">
        <DialogHeader className="border-b border-border/60 pb-4">
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <Upload className="w-5 h-5 text-primary" />
            Upload Dataset Wizard
          </DialogTitle>
          <DialogDescription className="text-muted-foreground mt-1 text-sm">
            Ingest your evaluation cases in JSON, JSONL, or CSV format. Map non-standard columns to our system fields.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4">
          <AnimatePresence mode="wait">
            
            {/* STEP 1: SELECT FILE */}
            {step === 'select' && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-4"
              >
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-muted-foreground/30 hover:border-primary/60 dark:hover:border-primary/50 bg-card hover:bg-accent/10 dark:bg-card/40 rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all duration-300 group"
                >
                  <Input 
                    ref={fileInputRef}
                    id="dataset-file" 
                    type="file" 
                    accept=".json,.jsonl,.csv"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <div className="p-4 rounded-full bg-primary/10 text-primary group-hover:scale-110 transition-transform duration-300">
                    <Upload className="w-8 h-8" />
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-base text-foreground">Click to upload or drag & drop</p>
                    <p className="text-xs text-muted-foreground mt-1">Accepts JSON, JSONL, and CSV formats</p>
                  </div>
                </div>

                {file && (
                  <div className="p-4 bg-muted/40 border border-border rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {file.name.endsWith('.csv') ? (
                        <FileSpreadsheet className="w-8 h-8 text-emerald-500" />
                      ) : (
                        <FileJson className="w-8 h-8 text-amber-500" />
                      )}
                      <div>
                        <p className="font-medium text-sm text-foreground truncate max-w-xs md:max-w-md">{file.name}</p>
                        <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                      </div>
                    </div>
                    {columns && (
                      <span className="text-xs font-semibold px-2.5 py-1 bg-primary/10 text-primary rounded-full">
                        {columns.length} columns detected
                      </span>
                    )}
                  </div>
                )}

                {/* Dataset Metadata */}
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <label htmlFor="dataset-name" className="text-xs font-semibold text-foreground">
                      Dataset Name <span className="text-muted-foreground font-normal">(optional — defaults to filename)</span>
                    </label>
                    <Input
                      id="dataset-name"
                      type="text"
                      value={datasetName}
                      onChange={(e) => setDatasetName(e.target.value)}
                      placeholder={file ? file.name.replace(/\.[^.]+$/, '') : "e.g. Customer Support Q3 2025"}
                      className="h-9 text-sm bg-background/50"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label htmlFor="dataset-description" className="text-xs font-semibold text-foreground">
                      Description <span className="text-muted-foreground font-normal">(optional)</span>
                    </label>
                    <Input
                      id="dataset-description"
                      type="text"
                      value={datasetDescription}
                      onChange={(e) => setDatasetDescription(e.target.value)}
                      placeholder="e.g. Held-out test cases for safety regression suite"
                      className="h-9 text-sm bg-background/50"
                    />
                  </div>
                </div>

                {warningMsg && (
                  <div className="flex items-start gap-2.5 p-3.5 text-sm text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg">
                    <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <p>{warningMsg}</p>
                  </div>
                )}

                {errorMsg && (
                  <div className="flex items-start gap-2.5 p-3.5 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <p>{errorMsg}</p>
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
                  <Button variant="outline" type="button" onClick={() => setOpen(false)} className="hover:bg-muted text-foreground">
                    Cancel
                  </Button>
                  <Button 
                    type="button" 
                    disabled={!file || !!errorMsg} 
                    onClick={() => setStep('mapping')}
                    className="bg-primary hover:bg-primary/95 text-primary-foreground"
                  >
                    Next: Map Schema
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </motion.div>
            )}

            {/* STEP 2: SCHEMA MAPPING */}
            {step === 'mapping' && columns && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-5"
              >
                {/* Schema Variables Guidance Panel */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 bg-muted/30 border border-border rounded-xl text-xs text-muted-foreground">
                  <div className="space-y-1">
                    <p className="font-semibold text-foreground flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                      Primary Query (<code className="font-mono text-primary">query</code>)
                    </p>
                    <p className="pl-2.5 leading-relaxed">The main text input evaluated by your pipeline. <span className="font-medium text-foreground">Required.</span></p>
                  </div>
                  <div className="space-y-1">
                    <p className="font-semibold text-foreground flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      Expected Output (<code className="font-mono text-primary">expected_output</code>)
                    </p>
                    <p className="pl-2.5 leading-relaxed">The ground truth target response (e.g. for semantic comparison).</p>
                  </div>
                  <div className="space-y-1">
                    <p className="font-semibold text-foreground flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                      Inputs (<code className="font-mono text-primary">inputs.*</code>)
                    </p>
                    <p className="pl-2.5 leading-relaxed">Extra prompt variables automatically bound to evaluation runtime (e.g. <code className="font-mono text-[10px]">temperature</code>).</p>
                  </div>
                  <div className="space-y-1">
                    <p className="font-semibold text-foreground flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                      Metadata (<code className="font-mono text-primary">metadata.*</code>)
                    </p>
                    <p className="pl-2.5 leading-relaxed">Non-evaluated tags used to filter, sort, or label test runs (e.g. <code className="font-mono text-[10px]">category</code>).</p>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                    <Settings2 className="w-4 h-4 text-primary" />
                    Align Columns with Internal Schema
                  </h3>
                  <Button 
                    type="button" 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setShowDataPreview(!showDataPreview)}
                    className="text-xs flex items-center gap-1 text-primary hover:text-primary/90 hover:bg-primary/5"
                  >
                    {showDataPreview ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    {showDataPreview ? "Hide File Preview" : "Show File Preview"}
                  </Button>
                </div>

                {/* Optional File Preview Drawer/Section */}
                {showDataPreview && previewRows && (
                  <div className="border border-border rounded-lg bg-card/50 overflow-x-auto max-h-[160px] text-xs">
                    <table className="min-w-full divide-y divide-border/60">
                      <thead className="bg-muted/40">
                        <tr>
                          {columns.map(col => (
                            <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40 bg-card/10">
                        {previewRows.map((row, idx) => (
                          <tr key={idx}>
                            {columns.map(col => (
                              <td key={col} className="px-3 py-2 text-foreground/80 truncate max-w-[150px]">{String(row[col] ?? '')}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Schema Mapping Form Table */}
                <div className="border border-border rounded-xl bg-card overflow-hidden">
                  <div className="grid grid-cols-12 gap-4 bg-muted/40 px-4 py-2 text-xs font-semibold text-muted-foreground border-b border-border/60">
                    <div className="col-span-4">Source Column</div>
                    <div className="col-span-8">Target Schema Variable</div>
                  </div>
                  <div className="divide-y divide-border/50 max-h-[260px] overflow-y-auto">
                    {columns.map(col => {
                      const currentVal = mapping[col] || 'exclude'
                      let mappedType: 'query' | 'output' | 'inputs' | 'metadata' | 'exclude' = 'exclude'
                      
                      if (currentVal === 'query') mappedType = 'query'
                      else if (currentVal === 'expected_output') mappedType = 'output'
                      else if (currentVal.startsWith('inputs.')) mappedType = 'inputs'
                      else if (currentVal.startsWith('metadata.')) mappedType = 'metadata'

                      return (
                        <div key={col} className="grid grid-cols-12 gap-4 items-center px-4 py-2.5 hover:bg-muted/10 transition-colors">
                          <div className="col-span-4 flex flex-col gap-0.5">
                            <span className="font-medium text-sm text-foreground truncate" title={col}>{col}</span>
                            {previewRows && previewRows[0] && (
                              <span className="text-xs text-muted-foreground truncate">
                                Ex: <span className="italic">"{String(previewRows[0][col] ?? '')}"</span>
                              </span>
                            )}
                          </div>
                          
                          <div className="col-span-8 flex gap-2 items-center">
                            <Select 
                              value={mappedType} 
                              onValueChange={(val) => {
                                if (val === 'query') handleMappingChange(col, 'query')
                                else if (val === 'output') handleMappingChange(col, 'expected_output')
                                else if (val === 'exclude') handleMappingChange(col, 'exclude')
                                else if (val === 'inputs') handleMappingChange(col, `inputs.${col}`)
                                else if (val === 'metadata') handleMappingChange(col, `metadata.${col}`)
                              }}
                            >
                              <SelectTrigger className="flex-1 text-xs h-9 bg-background/50 border-border">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent className="text-xs bg-popover text-popover-foreground border-border">
                                <SelectItem value="query">Primary Query (query)</SelectItem>
                                <SelectItem value="output">Expected Output (expected_output)</SelectItem>
                                <SelectItem value="inputs">Custom Input Variable (inputs.*)</SelectItem>
                                <SelectItem value="metadata">Metadata Variable (metadata.*)</SelectItem>
                                <SelectItem value="exclude">Exclude Column</SelectItem>
                              </SelectContent>
                            </Select>

                            {/* Contextual customization field for custom inputs or metadata names */}
                            {(mappedType === 'inputs' || mappedType === 'metadata') && (
                              <Input 
                                type="text"
                                value={currentVal.split('.', 2)[1] || ""}
                                onChange={(e) => {
                                  const name = e.target.value.replace(/[^a-zA-Z0-9_]/g, '')
                                  handleMappingChange(col, `${mappedType}.${name}`)
                                }}
                                className="w-36 h-9 text-xs font-mono bg-background/50 border-border"
                                placeholder="variable name"
                              />
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {!isQueryMapped && (
                  <div className="flex items-start gap-2.5 p-3.5 text-xs text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <p className="font-medium">Mandatory requirement: Exactly one column must be mapped to the Primary Query (query) target.</p>
                  </div>
                )}

                <div className="flex justify-between items-center pt-4 border-t border-border/40">
                  <Button variant="outline" type="button" onClick={() => setStep('select')} className="hover:bg-muted text-foreground">
                    Back
                  </Button>
                  <Button 
                    type="submit" 
                    onClick={handleUpload}
                    disabled={!isQueryMapped} 
                    className="bg-primary hover:bg-primary/95 text-primary-foreground"
                  >
                    Upload and Ingest
                  </Button>
                </div>
              </motion.div>
            )}

            {/* STEP 3: UPLOADING */}
            {step === 'uploading' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="py-12 flex flex-col items-center justify-center gap-6"
              >
                <div className="relative w-24 h-24 flex items-center justify-center">
                  <svg className="w-full h-full rotate-270">
                    <circle cx="48" cy="48" r="40" stroke="currentColor" className="text-muted/30" strokeWidth="6" fill="transparent" />
                    <circle cx="48" cy="48" r="40" stroke="currentColor" className="text-primary transition-all duration-300" strokeWidth="6" fill="transparent"
                      strokeDasharray={251.2}
                      strokeDashoffset={251.2 - (251.2 * uploadProgress) / 100}
                    />
                  </svg>
                  <span className="absolute text-lg font-bold text-foreground">{uploadProgress}%</span>
                </div>
                <div className="text-center space-y-1">
                  <h4 className="font-semibold text-lg text-foreground">Uploading dataset...</h4>
                  <p className="text-sm text-muted-foreground">Please keep this dialog open. Processing rows on server.</p>
                </div>
              </motion.div>
            )}

            {/* STEP 4: SUCCESS */}
            {step === 'success' && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="py-10 flex flex-col items-center justify-center gap-5"
              >
                <div className="p-4 rounded-full bg-emerald-500/10 text-emerald-500 scale-110">
                  <CheckCircle2 className="w-12 h-12" />
                </div>
                <div className="text-center space-y-2">
                  <h4 className="font-bold text-xl text-foreground">Ingestion Complete</h4>
                  <p className="text-sm text-muted-foreground max-w-sm">The dataset was successfully parsed, mapped, and persisted to your data workspace.</p>
                </div>
                <div className="pt-6 w-full flex justify-center border-t border-border/40 mt-4">
                  <Button onClick={() => setOpen(false)} className="bg-primary hover:bg-primary/95 text-primary-foreground min-w-[120px]">
                    Done
                  </Button>
                </div>
              </motion.div>
            )}

            {/* STEP 5: ERROR */}
            {step === 'error' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="py-8 space-y-4"
              >
                <div className="flex flex-col items-center justify-center gap-4 text-center">
                  <div className="p-3 rounded-full bg-destructive/10 text-destructive">
                    <AlertCircle className="w-10 h-10" />
                  </div>
                  <div>
                    <h4 className="font-bold text-lg text-foreground">Ingestion Failed</h4>
                    <p className="text-sm text-red-400 mt-2 p-3 bg-red-400/10 border border-red-400/20 rounded-lg max-w-md break-all">{errorMsg}</p>
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-6 border-t border-border/40 mt-4">
                  <Button variant="outline" onClick={() => setStep('mapping')} className="text-foreground">
                    Go Back & Adjust Mapping
                  </Button>
                  <Button onClick={resetState} className="bg-primary hover:bg-primary/95 text-primary-foreground">
                    Start Over
                  </Button>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </DialogContent>
    </Dialog>
  )
}
