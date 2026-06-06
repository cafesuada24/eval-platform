"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Plus, Loader2, RefreshCw } from "lucide-react";
import { TestCase, Dataset, FileAsset } from "@/types/dataset";
import { fetchTestCases, deleteTestCase, updateTestCase, createTestCase, fetchDocuments } from "@/lib/api/datasets";
import { Button } from "@/components/ui/button";
import { TestCaseCard } from "./TestCaseCard";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";

interface TestCaseListProps {
  dataset: Dataset;
  files: FileAsset[];
}

export function TestCaseList({ dataset, files }: TestCaseListProps) {
  const [cases, setCases] = useState<TestCase[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  const loadData = useCallback(async (pageNum: number, append = false) => {
    try {
      setIsLoading(true);
      const data = await fetchTestCases(dataset.id, pageNum, 20); // using limit=20
      
      if (append) {
        setCases(prev => [...prev, ...data.items]);
      } else {
        setCases(data.items);
      }
      
      setHasMore(data.total > pageNum * data.limit);
      setPage(pageNum);
    } catch (error) {
      toast.error("Failed to load test cases");
    } finally {
      setIsLoading(false);
    }
  }, [dataset.id]);

  useEffect(() => {
    loadData(1);
  }, [loadData]);

  const handleUpdate = async (id: string, data: Omit<TestCase, "id">) => {
    try {
      const updated = await updateTestCase(dataset.id, id, data);
      setCases(prev => prev.map(c => c.id === id ? updated : c));
      toast.success("Test case saved");
    } catch (error) {
      toast.error("Failed to save test case");
      throw error; // Re-throw so the card knows it failed
    }
  };

  const handleDelete = async (id: string) => {
    // Optimistic UI update
    const previousCases = [...cases];
    setCases(prev => prev.filter(c => c.id !== id));
    
    try {
      await deleteTestCase(dataset.id, id);
      toast.success("Test case deleted");
    } catch (error) {
      // Revert optimistic update
      setCases(previousCases);
      toast.error("Failed to delete test case");
      throw error;
    }
  };

  const handleCreate = async () => {
    try {
      setIsCreating(true);
      // Prepopulate keys based on schema
      const initialInputs: Record<string, string> = {};
      const initialOutputs: Record<string, string> = {};
      
      if (dataset.schema?.inputs) {
        Object.keys(dataset.schema.inputs).forEach(k => initialInputs[k] = "");
      }
      if (dataset.schema?.outputs) {
        Object.keys(dataset.schema.outputs).forEach(k => initialOutputs[k] = "");
      }

      const newCase = await createTestCase(dataset.id, {
        inputs: initialInputs,
        expected_outputs: initialOutputs,
        metadata: {},
      });
      // Add to top of list
      setCases(prev => [newCase, ...prev]);
      toast.success("Test case created");
    } catch (error) {
      toast.error("Failed to create test case");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center sticky top-0 bg-background/80 backdrop-blur-md z-10 py-4 border-b border-border">
        <h2 className="text-sm font-semibold text-foreground font-mono uppercase tracking-wider">Test Cases ({cases.length})</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => loadData(1)} disabled={isLoading} className="border-border text-foreground hover:bg-muted rounded-[2px] font-mono text-[10px] uppercase tracking-wider h-8">
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={handleCreate} disabled={isCreating} className="bg-primary hover:bg-primary/95 text-primary-foreground rounded-[2px] font-mono text-[10px] uppercase tracking-wider h-8">
            {isCreating ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Plus className="h-3.5 w-3.5 mr-1.5" />}
            New Case
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        {cases.map((testCase) => (
          <TestCaseCard
            key={testCase.id}
            testCase={testCase}
            schema={dataset.schema}
            documents={files}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
          />
        ))}

        {isLoading && cases.length === 0 && (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <Skeleton key={i} className="h-[200px] w-full rounded-xl bg-card" />
            ))}
          </div>
        )}

        {!isLoading && cases.length === 0 && (
          <div className="text-center py-12 px-4 border border-border border-dashed rounded-xl bg-card/50">
            <div className="text-muted-foreground mb-4">No test cases found in this dataset.</div>
            <Button onClick={handleCreate} disabled={isCreating} variant="outline" className="border-primary/30 text-primary hover:bg-primary/10">
              <Plus className="h-4 w-4 mr-2" /> Add First Case
            </Button>
          </div>
        )}
      </div>

      {hasMore && cases.length > 0 && (
        <div className="flex justify-center pt-6 pb-12">
          <Button
            variant="outline"
            onClick={() => loadData(page + 1, true)}
            disabled={isLoading}
            className="border-border text-foreground hover:bg-muted rounded-[2px] font-mono text-[10px] uppercase tracking-wider h-8"
          >
            {isLoading && <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />}
            Load More
          </Button>
        </div>
      )}
    </div>
  );
}
