import { useEffect, useState } from "react";
import { fetchStats, fetchHistory } from "./api";
import type { DashboardStats, ScanRecord } from "./types";

type LoadState = "loading" | "ready" | "error";

export default function App() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [status, setStatus] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setStatus("loading");
      try {
        const [statsRes, historyRes] = await Promise.all([
          fetchStats(),
          fetchHistory(),
        ]);
        if (cancelled) return;
        setStats(statsRes);
        setScans(historyRes.history);
        setStatus("ready");
      } catch (err) {
        if (cancelled) return;
        setErrorMessage(err instanceof Error ? err.message : "Unknown error");
        setStatus("error");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page">
      <header className="header">
        <h1>🛣️ Road Guardian</h1>
        <p className="subtitle">Live pothole detection dashboard</p>
      </header>

      {status === "loading" && <p className="status">Loading dashboard…</p>}

      {status === "error" && (
        <p className="status error">
          Could not reach the backend ({errorMessage}). Is Flask running on
          port 5000?
        </p>
      )}

      {status === "ready" && stats && (
        <>
          <section className="stat-grid">
            <StatCard label="Images Processed" value={stats.images_processed} />
            <StatCard label="Potholes Detected" value={stats.total_potholes_detected} />
            <StatCard label="High Severity" value={stats.severity_totals.High} tone="high" />
            <StatCard label="Medium Severity" value={stats.severity_totals.Medium} tone="medium" />
            <StatCard label="Low Severity" value={stats.severity_totals.Low} tone="low" />
          </section>

          <section className="feed">
            <h2>Recent Scans</h2>
            {scans.length === 0 ? (
              <p className="status">No scans logged yet this session.</p>
            ) : (
              <ul className="feed-list">
                {scans.map((scan) => (
                  <ScanRow key={scan.id} scan={scan} />
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: number;
  tone?: "high" | "medium" | "low";
}

function StatCard({ label, value, tone }: StatCardProps) {
  return (
    <div className={`stat-card ${tone ?? ""}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

function ScanRow({ scan }: { scan: ScanRecord }) {
  // A scan is "highest severity" for its accent color — High > Medium > Low.
  const topSeverity = scan.severity_counts.High > 0
    ? "high"
    : scan.severity_counts.Medium > 0
    ? "medium"
    : "low";

  return (
    <li className={`feed-item ${topSeverity}`}>
      <span className="badge">{scan.filename}</span>
      <span className="confidence">
        {scan.total_detections} pothole{scan.total_detections === 1 ? "" : "s"}
        {" "}(H:{scan.severity_counts.High} M:{scan.severity_counts.Medium} L:{scan.severity_counts.Low})
      </span>
      <span className="timestamp">{scan.timestamp}</span>
    </li>
  );
}
