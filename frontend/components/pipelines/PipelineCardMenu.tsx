"use client"

import { useRouter } from "next/navigation"
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { toast } from "sonner"
import { getApiBaseUrl } from "@/lib/utils"

interface PipelineCardMenuProps {
  pipelineId: string
  pipelineName: string
}

const API_BASE_URL = getApiBaseUrl()

export function PipelineCardMenu({ pipelineId, pipelineName }: PipelineCardMenuProps) {
  const router = useRouter()

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm(`Delete pipeline "${pipelineName}"? This cannot be undone.`)) return
    try {
      const res = await fetch(`${API_BASE_URL}/v1/configs/pipelines/${pipelineId}`, {
        method: "DELETE",
      })
      if (!res.ok) throw new Error("Failed to delete")
      toast.success(`Pipeline "${pipelineName}" deleted`)
      router.refresh()
    } catch {
      toast.error("Failed to delete pipeline")
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-[2px] opacity-0 group-hover:opacity-100 transition-opacity shrink-0 text-muted-foreground hover:text-foreground"
            onClick={(e) => { e.preventDefault(); e.stopPropagation() }}
          />
        }
      >
        <MoreHorizontal className="w-4 h-4" />
        <span className="sr-only">Pipeline options</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44 rounded-[2px]">
        <DropdownMenuItem
          className="gap-2 cursor-pointer"
          onClick={(e) => { e.stopPropagation(); router.push(`/pipelines/${pipelineId}`) }}
        >
          <Pencil className="w-3.5 h-3.5" />
          Edit pipeline
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="gap-2 cursor-pointer text-destructive focus:text-destructive"
          onClick={handleDelete}
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
