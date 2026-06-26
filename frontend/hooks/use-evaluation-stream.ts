"use client";

import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { swrFetcher } from "@/hooks/use-swr-fetcher";
import { PipelineRunResult } from "@/lib/api/evaluations";
import { getApiBaseUrl } from "@/lib/utils";

const API_BASE = getApiBaseUrl();

export function useEvaluationStream(
  evaluationId: string,
  initialPipelines: PipelineRunResult[],
  initialIsComplete = false
) {
  const [pipelines, setPipelines] = useState<PipelineRunResult[]>(initialPipelines);
  const [isComplete, setIsComplete] = useState(initialIsComplete);
  const [useFallback, setUseFallback] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  // SSE path
  useEffect(() => {
    if (isComplete) return;

    const es = new EventSource(`${API_BASE}/v1/evaluations/${evaluationId}/stream`);
    esRef.current = es;

    es.addEventListener("testcase_complete", (e) => {
      const result: PipelineRunResult = JSON.parse(e.data);
      setPipelines((prev) => {
        const idx = prev.findIndex((p) => p.run_id === result.run_id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = result;
          return next;
        }
        return [...prev, result];
      });
    });

    es.addEventListener("job_complete", () => {
      setIsComplete(true);
      es.close();
    });

    es.onerror = () => {
      es.close();
      setUseFallback(true);
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [evaluationId, isComplete]);

  // SWR fallback — only activates if SSE failed
  const { data: fallbackPipelines } = useSWR<PipelineRunResult[]>(
    useFallback && !isComplete ? `${API_BASE}/v1/evaluations/${evaluationId}/pipelines` : null,
    swrFetcher,
    { refreshInterval: 5000 }
  );

  useEffect(() => {
    if (fallbackPipelines) {
      setPipelines(fallbackPipelines);
    }
  }, [fallbackPipelines]);

  return { pipelines, isComplete };
}
