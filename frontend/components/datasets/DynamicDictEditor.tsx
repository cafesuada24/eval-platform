"use client";

import React, { useState, useEffect, useRef } from "react";
import { FileAsset } from "@/types/dataset";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Trash2, Plus, Code, List, AlertCircle, Lock } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SchemaDictEditorProps {
  value: Record<string, any>;
  onChange: (value: Record<string, any>) => void;
  label: string;
  schemaDef?: Record<string, string>; // Predefined schema definition
  documents?: FileAsset[];
}

interface KeyValuePair {
  id: string;
  key: string;
  value: any;
  isCustom: boolean;
}

// Helper to convert array of pairs to dictionary
function arrayToDict(arr: KeyValuePair[]): Record<string, any> {
  const dict: Record<string, any> = {};
  for (const item of arr) {
    if (item.key.trim() !== "") {
      dict[item.key] = item.value;
    }
  }
  return dict;
}

// Helper to check if two dictionaries are equivalent
function dictEquals(d1: Record<string, any>, d2: Record<string, any>): boolean {
  const keys1 = Object.keys(d1 || {});
  const keys2 = Object.keys(d2 || {});
  if (keys1.length !== keys2.length) return false;
  return keys1.every(k => d1[k] === d2[k]);
}

export function SchemaDictEditor({ value, onChange, label, schemaDef, documents }: SchemaDictEditorProps) {
  const [mode, setMode] = useState<"visual" | "code">("visual");
  const [localArray, setLocalArray] = useState<KeyValuePair[]>([]);
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  
  // Track previous value to avoid circular updates
  const prevValueRef = useRef<Record<string, any>>(value || {});

  // Sync value from parent to local visual array
  useEffect(() => {
    const currentValue = value || {};
    if (!dictEquals(currentValue, prevValueRef.current) || localArray.length === 0) {
      prevValueRef.current = currentValue;
      
      const schemaKeys = Object.keys(schemaDef || {});
      const valueKeys = Object.keys(currentValue);
      const allKeys = Array.from(new Set([...schemaKeys, ...valueKeys]));
      
      const newArray = allKeys.map(key => {
        const isCustom = schemaDef ? !(key in schemaDef) : true;
        const val = currentValue[key] !== undefined ? currentValue[key] : "";
        
        // Find existing ID if available to prevent key re-registration focus jumps
        const existing = localArray.find(item => item.key === key);
        
        return {
          id: existing ? existing.id : `${key}-${Math.random().toString(36).substring(2, 9)}`,
          key,
          value: val,
          isCustom,
        };
      });
      
      setLocalArray(newArray);
    }
  }, [value, schemaDef]);

  // Sync Visual State to Parent
  const handleVisualChange = (updatedArray: KeyValuePair[]) => {
    setLocalArray(updatedArray);
    const newDict = arrayToDict(updatedArray);
    prevValueRef.current = newDict;
    onChange(newDict);
  };

  // Toggle Mode
  const toggleMode = (newMode: "visual" | "code") => {
    if (newMode === "code") {
      setJsonText(JSON.stringify(value || {}, null, 2));
      setJsonError(null);
    } else {
      // Switch back to visual - rebuild array from current value
      const schemaKeys = Object.keys(schemaDef || {});
      const valueKeys = Object.keys(value || {});
      const allKeys = Array.from(new Set([...schemaKeys, ...valueKeys]));
      const newArray = allKeys.map(key => ({
        id: `${key}-${Math.random().toString(36).substring(2, 9)}`,
        key,
        value: (value || {})[key] !== undefined ? (value || {})[key] : "",
        isCustom: schemaDef ? !(key in schemaDef) : true,
      }));
      setLocalArray(newArray);
    }
    setMode(newMode);
  };

  // Visual Form Handlers
  const handleKeyNameChange = (id: string, newKeyName: string) => {
    const updated = localArray.map(item => 
      item.id === id ? { ...item, key: newKeyName } : item
    );
    handleVisualChange(updated);
  };

  const handleValueChange = (id: string, newValue: any) => {
    const updated = localArray.map(item => 
      item.id === id ? { ...item, value: newValue } : item
    );
    handleVisualChange(updated);
  };

  const handleRemoveField = (id: string) => {
    const updated = localArray.filter(item => item.id !== id);
    handleVisualChange(updated);
  };

  const handleAddField = () => {
    // Generate a unique name
    let count = 1;
    let newKey = `custom_field_${count}`;
    while (localArray.some(item => item.key === newKey)) {
      count++;
      newKey = `custom_field_${count}`;
    }

    const newRow: KeyValuePair = {
      id: `custom-${Math.random().toString(36).substring(2, 9)}`,
      key: newKey,
      value: "",
      isCustom: true,
    };

    const updated = [...localArray, newRow];
    handleVisualChange(updated);
  };

  // Code Mode Handlers
  const handleJsonChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setJsonText(text);

    try {
      if (text.trim() === "") {
        setJsonError(null);
        prevValueRef.current = {};
        onChange({});
        return;
      }
      
      const parsed = JSON.parse(text);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("JSON must be a valid key-value object");
      }
      setJsonError(null);
      prevValueRef.current = parsed;
      onChange(parsed);
    } catch (err: any) {
      setJsonError(err.message);
    }
  };

  const handleJsonBlur = () => {
    // Prettify on blur if valid
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, 2));
      setJsonError(null);
    } catch (err) {}
  };

  // Helper to identify keys that denote uploaded file attachments
  const isFileField = (key: string): boolean => {
    const k = key.toLowerCase();
    return k === "image_id" || k.endsWith("_id") || k.endsWith("_file");
  };

  return (
    <div className="space-y-4">
      {/* Header with Custom Segmented Mode Toggles */}
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-foreground/80 font-mono tracking-widest uppercase">
          {label}
        </h4>
        
        <div className="flex bg-muted/40 p-0.5 rounded-[2px] border border-border/60">
          <button
            type="button"
            onClick={() => toggleMode("visual")}
            className={`px-2 py-1 text-[10px] font-mono tracking-tight uppercase transition-all duration-150 rounded-[1px] ${
              mode === "visual"
                ? "bg-card text-foreground shadow-sm font-semibold border border-border/40"
                : "text-muted-foreground hover:text-foreground border border-transparent"
            }`}
          >
            Form
          </button>
          <button
            type="button"
            onClick={() => toggleMode("code")}
            className={`px-2 py-1 text-[10px] font-mono tracking-tight uppercase transition-all duration-150 rounded-[1px] ${
              mode === "code"
                ? "bg-card text-foreground shadow-sm font-semibold border border-border/40"
                : "text-muted-foreground hover:text-foreground border border-transparent"
            }`}
          >
            JSON
          </button>
        </div>
      </div>

      {/* Editor Content Area */}
      <div className="min-h-[140px]">
        {mode === "visual" ? (
          <div className="space-y-3.5">
            {localArray.length === 0 ? (
              <div className="text-xs text-muted-foreground italic py-6 text-center border border-border/40 border-dashed rounded-[2px]">
                No fields present. Click "Add Custom Field" to start.
              </div>
            ) : (
              <div className="space-y-3">
                <AnimatePresence initial={false}>
                  {localArray.map((item, idx) => {
                    const isFile = isFileField(item.key);
                    const schemaDescription = schemaDef ? schemaDef[item.key] : undefined;

                    return (
                      <motion.div
                        key={item.id}
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        className="flex items-start gap-2 group"
                      >
                        {/* Key Name Input / Label */}
                        <div className="w-1/3 flex-shrink-0">
                          {item.isCustom ? (
                            <Input
                              value={item.key}
                              onChange={(e) => handleKeyNameChange(item.id, e.target.value)}
                              placeholder="Key name"
                              className="font-mono text-xs bg-background border-border hover:border-primary/50 focus-visible:ring-primary/30 h-9 rounded-[2px]"
                            />
                          ) : (
                            <div 
                              className="h-9 px-3 flex items-center justify-between border border-border/50 bg-muted/20 rounded-[2px] cursor-not-allowed text-xs font-mono font-medium text-foreground select-none"
                              title={schemaDescription || "System-defined schema parameter"}
                            >
                              <span className="truncate">{item.key}</span>
                              <Lock className="h-3 w-3 text-muted-foreground/60 flex-shrink-0 ml-1.5" />
                            </div>
                          )}
                        </div>

                        {/* Value Input / Dropdown */}
                        <div className="flex-1 min-w-0">
                          {isFile ? (
                            <Select
                              value={item.value || "none"}
                              onValueChange={(val) => handleValueChange(item.id, val === "none" ? "" : val)}
                            >
                              <SelectTrigger className="h-9 w-full text-xs font-mono bg-background border-border hover:border-primary/50 focus:ring-primary/30 rounded-[2px]">
                                <SelectValue placeholder="Select asset..." />
                              </SelectTrigger>
                              <SelectContent className="rounded-[2px] border-border bg-card">
                                <SelectItem value="none" className="text-muted-foreground italic font-mono text-xs">
                                  No asset selected
                                </SelectItem>
                                {documents?.map(doc => (
                                  <SelectItem key={doc.file_id} value={doc.file_id} className="font-mono text-xs">
                                    {doc.filename}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : (
                            <Input
                              value={item.value}
                              onChange={(e) => handleValueChange(item.id, e.target.value)}
                              placeholder={schemaDescription ? `Value (${schemaDescription})` : "Value"}
                              className="font-mono text-xs bg-background border-border hover:border-primary/50 focus-visible:ring-primary/30 h-9 rounded-[2px]"
                            />
                          )}
                        </div>

                        {/* Delete Field Button */}
                        {item.isCustom ? (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRemoveField(item.id)}
                            className="h-9 w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-[2px] transition-colors flex-shrink-0"
                            title="Remove Field"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        ) : (
                          <div className="w-9 h-9 flex-shrink-0" />
                        )}
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>
            )}

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddField}
              className="w-full border-dashed border-border hover:border-primary/60 hover:bg-primary/5 text-muted-foreground hover:text-foreground font-mono text-[10px] tracking-wider uppercase h-8 rounded-[2px] transition-all"
            >
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Add Custom Field
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <textarea
              value={jsonText}
              onChange={handleJsonChange}
              onBlur={handleJsonBlur}
              placeholder={'{\n  "key": "value"\n}'}
              className="w-full min-h-[160px] p-3.5 font-mono text-xs bg-background/50 border border-border hover:border-primary/50 focus:border-primary/70 focus:outline-none rounded-[2px] leading-relaxed resize-y"
            />
            {jsonError && (
              <motion.div
                initial={{ opacity: 0, y: -2 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-2 text-[10px] font-mono text-destructive bg-destructive/5 border border-destructive/20 p-2.5 rounded-[2px]"
              >
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5 text-destructive" />
                <span className="leading-normal">Invalid JSON syntax: {jsonError}</span>
              </motion.div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
