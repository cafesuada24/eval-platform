import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2, TestTube, CheckCircle2, FileText, Lightbulb } from "lucide-react";
import { toast } from "sonner";
import { MetricConfig } from "@/app/playground/page";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { motion, AnimatePresence } from "framer-motion";

interface RuntimeInspectorModalProps {
  runtimeId: string | null;
  metricId: string | null;
  isOpen: boolean;
  onClose: () => void;
  metricConfig: MetricConfig;
}

interface RuntimeState {
  usage?: {
    latency_ms: number;
    input_tokens: number;
    output_tokens: number;
  };
}

interface MetricRunResult {
  metric_id: string;
  score: number;
  justification: string;
  evidence: string | null;
  improvements?: string;
  assertion_status: number;
  run_id: string;
}

export function RuntimeInspectorModal({ runtimeId, metricId, isOpen, onClose, metricConfig }: RuntimeInspectorModalProps) {
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [runtimeState, setRuntimeState] = useState<RuntimeState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState<MetricRunResult | null>(null);
  const [isResultModalOpen, setIsResultModalOpen] = useState(false);

  useEffect(() => {
    if (isOpen && runtimeId) {
      // Fetch variables extracted from the runtime
      const fetchVariables = async () => {
        setIsLoading(true);
        try {
          const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          const keysParam = metricConfig?.required_inputs?.length ? `?keys=${encodeURIComponent(metricConfig.required_inputs.join(','))}` : '';
          
          const [varsRes, stateRes] = await Promise.all([
            fetch(`${baseUrl}/v1/runtimes/${runtimeId}/variables${keysParam}`),
            fetch(`${baseUrl}/v1/runtimes/${runtimeId}`)
          ]);

          if (varsRes.ok) {
            const data = await varsRes.json();
            setVariables(data || {});
          } else {
            console.error("Failed to fetch runtime variables");
            toast.error("Failed to fetch runtime variables.");
          }

          if (stateRes.ok) {
            const stateData = await stateRes.json();
            setRuntimeState(stateData);
          }
        } catch (err) {
          console.error("Error fetching runtime variables:", err);
        } finally {
          setIsLoading(false);
        }
      };
      
      fetchVariables();
    }
  }, [isOpen, runtimeId, metricConfig?.required_inputs]);

  const handleEvaluate = async () => {
    if (!runtimeId || !metricId) {
      toast.error("Missing runtime ID or metric ID.");
      return;
    }
    
    setIsEvaluating(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const payload = {
        inputs: variables
      };
      
      const res = await fetch(`${baseUrl}/v1/evaluations/metrics/${metricId}/run/${runtimeId}?building_mode=true`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        throw new Error(await res.text());
      }
      
      const data = await res.json();
      setEvaluationResult(data);
      setIsResultModalOpen(true);
      toast.success("Evaluation completed successfully.");
    } catch (err: unknown) {
      console.error(err);
      const msg = err instanceof Error ? err.message : 'Unknown error';
      toast.error(`Evaluation failed: ${msg}`);
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="sm:max-w-4xl w-[95vw] max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden">
          <DialogHeader className="p-6 border-b border-border/50 bg-muted/20 shrink-0">
            <DialogTitle className="flex items-center gap-2 text-xl">
              <TestTube className="w-5 h-5 text-emerald-500" />
              Runtime variables
            </DialogTitle>
            <DialogDescription>
              Inspect the variables extracted for runtime <code className="bg-muted px-1 py-0.5 rounded text-xs">{runtimeId}</code>.
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex-1 overflow-y-auto p-8">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin mb-4 text-emerald-500" />
                <p>Extracting runtime variables...</p>
              </div>
            ) : (
              <div className="space-y-8">
                <div>
                  <h3 className="font-semibold text-xs uppercase tracking-[0.1em] text-muted-foreground/80 border-b border-border/50 pb-3 mb-6">
                    Extracted Variables
                  </h3>
                  
                  {(!metricConfig?.required_inputs || metricConfig.required_inputs.length === 0) ? (
                    <div className="p-8 bg-muted/20 rounded-xl text-sm text-muted-foreground border border-dashed border-muted-foreground/20 text-center">
                      No required inputs defined for this metric.
                    </div>
                  ) : (
                    <Accordion className="w-full space-y-4">
                      {metricConfig.required_inputs.map((key) => (
                        <AccordionItem key={key} value={key} className="border border-border/50 rounded-xl bg-background shadow-sm overflow-hidden px-4">
                          <AccordionTrigger className="hover:no-underline py-4">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold font-mono text-emerald-600/90 flex items-center gap-1 bg-emerald-500/10 px-2 py-1 rounded-md border border-emerald-500/20">
                                {key}
                              </span>
                              {(!variables[key] || variables[key] === "") && (
                                <span className="text-[10px] uppercase font-bold text-muted-foreground/50 bg-muted px-1.5 py-0.5 rounded">Empty</span>
                              )}
                            </div>
                          </AccordionTrigger>
                          <AccordionContent>
                            <div className="p-4 bg-muted/30 border border-border/50 rounded-xl font-mono text-[13px] text-foreground/80 whitespace-pre-wrap max-h-[300px] overflow-y-auto shadow-[inset_0_1px_4px_rgba(0,0,0,0.02)] leading-relaxed mb-4">
                              {(variables[key] !== undefined && variables[key] !== null && variables[key] !== "") 
                                ? variables[key] 
                                : <span className="text-muted-foreground/40 italic">No value extracted from trace</span>}
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      ))}
                    </Accordion>
                  )}
                </div>
                
                {/* Resource Usage Metadata */}
                {runtimeState?.usage && (
                  <div>
                    <h4 className="font-semibold text-xs uppercase tracking-[0.1em] text-muted-foreground/80 border-b border-border/50 pb-3 mb-6">
                      Runtime Telemetry
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="p-4 bg-muted/20 rounded-xl border border-border/30 flex flex-col items-start gap-1">
                        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Latency</span>
                        <span className="font-mono text-lg font-medium">{runtimeState.usage.latency_ms} ms</span>
                      </div>
                      <div className="p-4 bg-muted/20 rounded-xl border border-border/30 flex flex-col items-start gap-1">
                        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Input Tokens</span>
                        <span className="font-mono text-lg font-medium">{runtimeState.usage.input_tokens}</span>
                      </div>
                      <div className="p-4 bg-muted/20 rounded-xl border border-border/30 flex flex-col items-start gap-1">
                        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Output Tokens</span>
                        <span className="font-mono text-lg font-medium">{runtimeState.usage.output_tokens}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          
          <div className="flex items-center justify-between p-4 border-t border-border/50 bg-muted/10 mt-auto shrink-0">
            <span className="text-xs text-muted-foreground hidden sm:inline-flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500/70" />
              Agent dynamically extracted this state
            </span>
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={onClose} className="shadow-sm">
                Close
              </Button>
              <Button 
                onClick={handleEvaluate} 
                disabled={isEvaluating || isLoading}
                className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-md shadow-emerald-500/10 transition-all active:scale-[0.98]"
              >
                {isEvaluating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Evaluating...
                  </>
                ) : (
                  <>
                    <TestTube className="w-4 h-4" />
                    Run Evaluation
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={isResultModalOpen} onOpenChange={setIsResultModalOpen}>
        <DialogContent className="sm:max-w-2xl bg-card border-border/50 shadow-2xl p-0 overflow-hidden">
          <AnimatePresence>
            {evaluationResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <DialogHeader className="p-8 border-b border-border/50 relative overflow-hidden bg-muted/10">
                  <DialogTitle className="text-3xl font-bold tracking-tight">
                    Evaluation Result
                  </DialogTitle>
                  <DialogDescription className="mt-2 text-base">
                    Review the metric score and justification details.
                  </DialogDescription>
                </DialogHeader>

                <div className="p-8 space-y-8">
                  <div className="flex justify-center">
                    <div className="flex flex-col items-center justify-center p-8 bg-background rounded-2xl border border-border shadow-sm w-full sm:w-1/2">
                      <span className="text-xs font-bold uppercase tracking-[0.15em] text-muted-foreground mb-4">Score</span>
                      <span className="text-6xl font-black font-mono tracking-tighter text-emerald-600 drop-shadow-sm">
                        {evaluationResult.score}
                      </span>
                    </div>
                  </div>

                  {evaluationResult.justification && (
                    <motion.div 
                      initial={{ opacity: 0 }} 
                      animate={{ opacity: 1 }} 
                      transition={{ delay: 0.1 }}
                      className="space-y-3"
                    >
                      <h4 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-muted-foreground">
                        <FileText className="w-4 h-4" />
                        Justification
                      </h4>
                      <div className="p-5 bg-muted/30 rounded-xl border border-border/50 leading-relaxed text-[15px] text-foreground/90 italic">
                        {evaluationResult.justification}
                      </div>
                    </motion.div>
                  )}

                  {evaluationResult.evidence && (
                    <motion.div 
                      initial={{ opacity: 0 }} 
                      animate={{ opacity: 1 }} 
                      transition={{ delay: 0.2 }}
                      className="space-y-3"
                    >
                      <h4 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-muted-foreground">
                        <FileText className="w-4 h-4" />
                        Evidence
                      </h4>
                      <div className="p-5 bg-muted/20 rounded-xl border border-border/50 leading-relaxed text-[14px] font-mono text-foreground/80 overflow-x-auto whitespace-pre-wrap">
                        {evaluationResult.evidence}
                      </div>
                    </motion.div>
                  )}

                  {evaluationResult.improvements && (
                    <motion.div 
                      initial={{ opacity: 0 }} 
                      animate={{ opacity: 1 }} 
                      transition={{ delay: 0.3 }}
                      className="space-y-3"
                    >
                      <h4 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-emerald-600/80">
                        <Lightbulb className="w-4 h-4" />
                        Suggested Improvements
                      </h4>
                      <div className="p-5 bg-emerald-500/5 rounded-xl border border-emerald-500/20 leading-relaxed text-[15px] text-foreground/90 whitespace-pre-wrap">
                        {evaluationResult.improvements}
                      </div>
                    </motion.div>
                  )}
                </div>

                <div className="p-6 border-t border-border/50 bg-muted/10 flex justify-end">
                  <Button onClick={() => setIsResultModalOpen(false)}>
                    Close Result
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </DialogContent>
      </Dialog>
    </>
  );
}
