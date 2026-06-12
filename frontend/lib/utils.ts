import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    const pad = (num: number) => String(num).padStart(2, "0");
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
  } catch {
    return "-";
  }
}

export function getAbsoluteFileUrl(url?: string): string {
  if (!url) return "";
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url)) {
    return url;
  }
  
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  let path = url;
  if (path.startsWith("/api/v1/")) {
    path = path.replace("/api/v1/", "/v1/");
  } else if (path.startsWith("api/v1/")) {
    path = "/" + path.replace("api/v1/", "v1/");
  }

  const cleanBase = apiBase.replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}


