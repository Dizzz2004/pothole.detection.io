import type { DashboardStats, HistoryResponse } from "./types";

// In dev, Vite's proxy (see vite.config.ts) forwards "/api/*" to the
// Flask backend at http://127.0.0.1:5000, so relative paths work as-is.
const BASE_URL = "/api";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`Request to ${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function fetchStats(): Promise<DashboardStats> {
  return getJSON<DashboardStats>("/stats");
}

export function fetchHistory(): Promise<HistoryResponse> {
  return getJSON<HistoryResponse>("/history");
}
