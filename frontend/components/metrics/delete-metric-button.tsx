"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { getApiBaseUrl } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function DeleteMetricButton({ metricId, metricName, disabled }: { metricId: string; metricName: string; disabled?: boolean }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const router = useRouter();

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const baseUrl = getApiBaseUrl();
      const res = await fetch(`${baseUrl}/v1/configs/metrics/${metricId}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error("Failed to delete metric");
      }

      toast.success(`Metric "${metricName}" deleted successfully`);
      setIsOpen(false);
      router.refresh();
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete metric. It might be used in a pipeline.");
    } finally {
      setIsDeleting(false);
    }
  };

  if (disabled) {
    return (
      <Button variant="ghost" size="icon" disabled className="opacity-50">
        <Trash2 className="w-4 h-4 text-destructive" />
        <span className="sr-only">Delete</span>
      </Button>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger render={<Button variant="ghost" size="icon" className="hover:text-destructive hover:bg-destructive/10" />}>
        <Trash2 className="w-4 h-4 text-destructive" />
        <span className="sr-only">Delete</span>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Are you absolutely sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete the metric 
            <span className="font-semibold text-foreground"> {metricName} </span>
            and remove it from our servers.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-3 mt-4">
          <Button variant="outline" onClick={() => setIsOpen(false)} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={(e) => {
              e.preventDefault();
              handleDelete();
            }}
            disabled={isDeleting}
          >
            {isDeleting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            Delete
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
