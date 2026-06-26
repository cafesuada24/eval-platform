import { RuntimeState } from "../types";
import { getApiBaseUrl } from "@/lib/utils";

const API_BASE_URL = getApiBaseUrl();

export async function getRuntimes(): Promise<RuntimeState[]> {
  const res = await fetch(`${API_BASE_URL}/v1/runtimes`, {
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error(`Failed to fetch runtimes: ${res.statusText}`);
  }
  return res.json();
}

export async function getRuntime(runtimeId: string): Promise<RuntimeState> {
  const res = await fetch(`${API_BASE_URL}/v1/runtimes/${runtimeId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch runtime: ${res.statusText}`);
  }
  return res.json();
}
