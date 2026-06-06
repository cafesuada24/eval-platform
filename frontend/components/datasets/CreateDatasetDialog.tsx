"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plus, X, ArrowRight, ArrowLeft } from "lucide-react"
import { toast } from "sonner"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { createDataset } from "@/lib/api/datasets"

export function CreateDatasetDialog() {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<1 | 2>(1)
  const [isCreating, setIsCreating] = useState(false)
  
  // Step 1
  const [name, setName] = useState("")
  
  // Step 2
  const [inputs, setInputs] = useState<{key: string, desc: string}[]>([
    { key: "query", desc: "string (Required: the main user input)" },
    { key: "image_id", desc: "string (Optional: ID of an uploaded image)" }
  ])
  const [outputs, setOutputs] = useState<{key: string, desc: string}[]>([
    { key: "expected_output", desc: "string (Optional: the ideal response)" }
  ])

  const router = useRouter()

  const handleReset = () => {
    setStep(1)
    setName("")
    setInputs([
      { key: "query", desc: "string (Required: the main user input)" },
      { key: "image_id", desc: "string (Optional: ID of an uploaded image)" }
    ])
    setOutputs([
      { key: "expected_output", desc: "string (Optional: the ideal response)" }
    ])
    setOpen(false)
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    setIsCreating(true)

    try {
      // Build schema object
      const schemaInputs: Record<string, string> = {}
      inputs.forEach(i => { if (i.key.trim()) schemaInputs[i.key.trim()] = i.desc.trim() })
      
      const schemaOutputs: Record<string, string> = {}
      outputs.forEach(o => { if (o.key.trim()) schemaOutputs[o.key.trim()] = o.desc.trim() })

      const schema = {
        inputs: schemaInputs,
        outputs: schemaOutputs
      }

      const newDataset = await createDataset(name.trim(), schema)
      toast.success("Dataset created successfully")
      handleReset()
      router.push(`/datasets/${newDataset.id}`)
    } catch (error) {
      toast.error("Error creating dataset")
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleReset(); else setOpen(true); }}>
      <DialogTrigger className={cn(buttonVariants({ variant: "default" }), "bg-primary text-primary-foreground hover:bg-primary")}>
        <Plus className="w-4 h-4 mr-2" />
        New Dataset
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl border-border bg-background text-foreground max-h-[85vh] overflow-y-auto overflow-x-hidden">
        <DialogHeader>
          <DialogTitle>Create New Dataset</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            {step === 1 ? "Name your dataset." : "Define the schema (variables) for your test cases."}
          </DialogDescription>
        </DialogHeader>
        
        {step === 1 ? (
          <form onSubmit={(e) => { e.preventDefault(); setStep(2); }} className="space-y-4 pt-4">
            <div className="grid w-full items-center gap-1.5">
              <label className="text-sm font-medium text-foreground">Dataset Name</label>
              <Input 
                id="name" 
                placeholder="e.g. Q4 Evaluation Data"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-card border-border focus-visible:ring-ring"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="outline" type="button" onClick={() => setOpen(false)} className="border-border text-foreground hover:bg-muted">
                Cancel
              </Button>
              <Button type="submit" disabled={!name.trim()} className="bg-primary hover:bg-primary text-primary-foreground">
                Next <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleCreate} className="space-y-6 pt-4">
            {/* Inputs Schema */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-foreground">Input Variables</h4>
                <Button 
                  type="button" 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setInputs([...inputs, {key: "", desc: ""}])}
                  className="h-7 px-2 text-xs text-primary hover:text-primary/80 hover:bg-primary/10"
                >
                  <Plus className="w-3 h-3 mr-1" /> Add Input
                </Button>
              </div>
              <div className="space-y-2">
                {inputs.map((item, idx) => (
                  <div key={`input-${idx}`} className="flex gap-2 items-start">
                    <Input 
                      placeholder="key (e.g. query)" 
                      value={item.key} 
                      disabled={item.key === "query"} // Force query to exist
                      onChange={(e) => {
                        const newInputs = [...inputs];
                        newInputs[idx].key = e.target.value;
                        setInputs(newInputs);
                      }}
                      className={cn("bg-card border-border w-1/3", item.key === "query" && "opacity-70 cursor-not-allowed")}
                    />
                    <Input 
                      placeholder="Description or type" 
                      value={item.desc} 
                      onChange={(e) => {
                        const newInputs = [...inputs];
                        newInputs[idx].desc = e.target.value;
                        setInputs(newInputs);
                      }}
                      className="bg-card border-border flex-1"
                    />
                    {item.key !== "query" && (
                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="icon" 
                        onClick={() => setInputs(inputs.filter((_, i) => i !== idx))}
                        className="text-muted-foreground hover:text-red-400 flex-shrink-0"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Outputs Schema */}
            <div className="space-y-3 pt-4 border-t border-border">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-foreground">Output Variables</h4>
                <Button 
                  type="button" 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setOutputs([...outputs, {key: "", desc: ""}])}
                  className="h-7 px-2 text-xs text-primary hover:text-primary/80 hover:bg-primary/10"
                >
                  <Plus className="w-3 h-3 mr-1" /> Add Output
                </Button>
              </div>
              <div className="space-y-2">
                {outputs.map((item, idx) => (
                  <div key={`output-${idx}`} className="flex gap-2 items-start">
                    <Input 
                      placeholder="key (e.g. expected_output)" 
                      value={item.key} 
                      onChange={(e) => {
                        const newOuts = [...outputs];
                        newOuts[idx].key = e.target.value;
                        setOutputs(newOuts);
                      }}
                      className="bg-card border-border w-1/3"
                    />
                    <Input 
                      placeholder="Description or type" 
                      value={item.desc} 
                      onChange={(e) => {
                        const newOuts = [...outputs];
                        newOuts[idx].desc = e.target.value;
                        setOutputs(newOuts);
                      }}
                      className="bg-card border-border flex-1"
                    />
                    <Button 
                      type="button" 
                      variant="ghost" 
                      size="icon" 
                      onClick={() => setOutputs(outputs.filter((_, i) => i !== idx))}
                      className="text-muted-foreground hover:text-red-400 flex-shrink-0"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-between items-center mt-8 pt-4 border-t border-border">
              <Button type="button" variant="ghost" onClick={() => setStep(1)} className="text-muted-foreground hover:text-foreground">
                <ArrowLeft className="w-4 h-4 mr-2" /> Back
              </Button>
              <div className="flex gap-3">
                <Button variant="outline" type="button" onClick={handleReset} className="border-border text-foreground hover:bg-muted">
                  Cancel
                </Button>
                <Button type="submit" disabled={isCreating || !inputs.find(i => i.key === "query")} className="bg-primary hover:bg-primary text-primary-foreground">
                  {isCreating ? "Creating..." : "Create Dataset"}
                </Button>
              </div>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
