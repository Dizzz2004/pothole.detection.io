// Types matched exactly against the real backend (app.py) responses.

export type Severity = "Low" | "Medium" | "High";

export interface SeverityCounts {
  Low: number;
  Medium: number;
  High: number;
}

export interface PotholeDetection {
  lat: number;
  lng: number;
  severity: Severity;
  confidence: number;
}

// One entry per POST /api/detect call (one uploaded image = one scan,
// which can contain multiple individual pothole detections).
export interface ScanRecord {
  id: string;
  filename: string;
  timestamp: string;
  total_detections: number;
  severity_counts: SeverityCounts;
  detections: PotholeDetection[];
}

// GET /api/history
export interface HistoryResponse {
  history: ScanRecord[];
}

// GET /api/stats
export interface DashboardStats {
  images_processed: number;
  total_potholes_detected: number;
  severity_totals: SeverityCounts;
  map_points: PotholeDetection[];
}
