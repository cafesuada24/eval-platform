"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { Trash2, Save, Loader2, RefreshCw } from "lucide-react";
import { TestCase, Dataset, FileAsset } from "@/types/dataset";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SchemaDictEditor } from "./DynamicDictEditor";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface TestCaseCardProps {
  testCase: TestCase;
  schema?: Dataset["schema"];
  documents?: FileAsset[];
  onUpdate: (id: string, data: Omit<TestCase, "id">) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export function TestCaseCard({ testCase, schema, documents, onUpdate, onDelete }: TestCaseCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  
  const form = useForm({
    defaultValues: {
      inputs: testCase.inputs || {},
      expected_outputs: testCase.expected_outputs || {},
      metadata: testCase.metadata || {},
    },
  });

  const { setValue, watch, handleSubmit, formState: { isDirty, isSubmitting, isValid } } = form;

  const onSubmit = async (data: any) => {
    if (!testCase.id) return;
    
    const updatedData: Omit<TestCase, "id"> = {
      inputs: data.inputs || {},
      expected_outputs: data.expected_outputs || {},
      metadata: data.metadata || {},
    };
    
    await onUpdate(testCase.id, updatedData);
    form.reset(data); // Reset form state to new values to clear isDirty
  };

  const handleDelete = async () => {
    if (!testCase.id) return;
    setIsDeleting(true);
    await onDelete(testCase.id);
  };

  return (
    <Card className="bg-card border-border p-5 rounded-[2px] transition-all duration-200 hover:border-primary/40 hover:shadow-md hover:shadow-primary/5">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        
        {/* Technical Monospace Header */}
        <div className="flex items-center justify-between pb-3 border-b border-border/50">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono uppercase bg-muted/40 text-muted-foreground px-2 py-0.5 rounded-[1px] border border-border/40 select-none">
              TestCase
            </span>
            <span className="text-xs font-mono text-muted-foreground truncate max-w-[200px]" title={testCase.id}>
              {testCase.id || "new-case"}
            </span>
          </div>
        </div>

        {/* Tabbed Interface for Inputs, Outputs, and Metadata */}
        <Tabs defaultValue="inputs" className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-muted/30 p-0.5 rounded-[2px] border border-border/40">
            <TabsTrigger 
              value="inputs" 
              className="rounded-[1px] font-mono text-[10px] tracking-wider uppercase data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:border-border/40 transition-all py-1.5"
            >
              Inputs
            </TabsTrigger>
            <TabsTrigger 
              value="outputs" 
              className="rounded-[1px] font-mono text-[10px] tracking-wider uppercase data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:border-border/40 transition-all py-1.5"
            >
              Outputs
            </TabsTrigger>
            <TabsTrigger 
              value="metadata" 
              className="rounded-[1px] font-mono text-[10px] tracking-wider uppercase data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:border-border/40 transition-all py-1.5"
            >
              Metadata
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="inputs" className="pt-4 focus-visible:outline-none">
            <div className="bg-background/40 p-4 rounded-[2px] border border-border/40 min-h-[220px]">
              <SchemaDictEditor
                value={watch("inputs")}
                onChange={(val) => setValue("inputs", val, { shouldDirty: true, shouldValidate: true })}
                label="Inputs"
                schemaDef={schema?.inputs}
                documents={documents}
              />
            </div>
          </TabsContent>
          
          <TabsContent value="outputs" className="pt-4 focus-visible:outline-none">
            <div className="bg-background/40 p-4 rounded-[2px] border border-border/40 min-h-[220px]">
              <SchemaDictEditor
                value={watch("expected_outputs")}
                onChange={(val) => setValue("expected_outputs", val, { shouldDirty: true, shouldValidate: true })}
                label="Outputs"
                schemaDef={schema?.outputs}
                documents={documents}
              />
            </div>
          </TabsContent>
          
          <TabsContent value="metadata" className="pt-4 focus-visible:outline-none">
            <div className="bg-background/40 p-4 rounded-[2px] border border-border/40 min-h-[220px]">
              <SchemaDictEditor
                value={watch("metadata")}
                onChange={(val) => setValue("metadata", val, { shouldDirty: true, shouldValidate: true })}
                label="Metadata"
                documents={documents}
              />
            </div>
          </TabsContent>
        </Tabs>

        {/* Action Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-border/50">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleDelete}
            disabled={isDeleting}
            className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-[2px] transition-colors font-mono text-[10px] uppercase tracking-wider h-8"
          >
            {isDeleting ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5 mr-1.5" />}
            Delete Case
          </Button>

          {isDirty && (
            <Button
              type="submit"
              size="sm"
              disabled={!isValid || isSubmitting}
              className="bg-primary hover:bg-primary/95 text-primary-foreground font-mono text-[10px] uppercase tracking-wider h-8 rounded-[2px] transition-all"
            >
              {isSubmitting ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1.5" />}
              Save Changes
            </Button>
          )}
        </div>
      </form>
    </Card>
  );
}
