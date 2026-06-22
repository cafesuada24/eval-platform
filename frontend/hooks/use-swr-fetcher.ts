/**
 * Shared SWR fetcher. Throws on non-OK responses so SWR surfaces them as errors.
 */
export async function swrFetcher<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    if (res.status === 404) return [] as unknown as T;
    throw new Error(`Fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
