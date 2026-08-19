// ============================================================
// Road Guardian — frontend logic
// Talks to the Flask backend API (same origin, /api/*)
// ============================================================

const API = {
  detect: "/api/detect",
  history: "/api/history",
  stats: "/api/stats",
  health: "/api/health",
};

let selectedFile = null;

// ---------------- Navigation ----------------
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`view-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "map") renderMap();
    if (btn.dataset.tab === "history") renderHistory();
    if (btn.dataset.tab === "dashboard") refreshStats();
  });
});

// ---------------- Health check ----------------
async function checkHealth() {
  const chip = document.getElementById("apiStatus");
  try {
    const res = await fetch(API.health);
    if (!res.ok) throw new Error();
    chip.className = "status-chip online";
    chip.innerHTML = `<span class="dot"></span>backend online`;
  } catch (e) {
    chip.className = "status-chip offline";
    chip.innerHTML = `<span class="dot"></span>backend offline`;
  }
}

// ---------------- Upload / dropzone ----------------
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const detectBtn = document.getElementById("detectBtn");
const confSlider = document.getElementById("confSlider");
const confVal = document.getElementById("confVal");

confSlider.addEventListener("input", () => confVal.textContent = confSlider.value);

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", e => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", e => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) handleFile(fileInput.files[0]);
});

function handleFile(file) {
  if (!file.type.startsWith("image/")) {
    alert("Please select an image file (JPG, PNG, WEBP).");
    return;
  }
  selectedFile = file;
  detectBtn.disabled = false;

  const reader = new FileReader();
  reader.onload = e => {
    dropzone.querySelector(".dropzone-inner").innerHTML =
      `<img class="preview" src="${e.target.result}" alt="preview" />
       <div class="dropzone-sub" style="margin-top:8px;">${file.name}</div>`;
  };
  reader.readAsDataURL(file);
}

detectBtn.addEventListener("click", runDetection);

async function runDetection() {
  if (!selectedFile) return;

  detectBtn.disabled = true;
  detectBtn.textContent = "Analyzing…";

  const resultArea = document.getElementById("resultArea");
  const table = document.getElementById("detectionTable");
  resultArea.innerHTML = `<div class="empty-state">Running detection pipeline…</div>`;
  table.innerHTML = "";

  const formData = new FormData();
  formData.append("image", selectedFile);

  try {
    const res = await fetch(`${API.detect}?confidence=${confSlider.value}`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      resultArea.innerHTML = `<div class="empty-state" style="color:var(--high)">${data.error || "Detection failed."}</div>`;
      return;
    }

    resultArea.innerHTML = `<img src="data:image/jpeg;base64,${data.annotated_image_base64}" alt="Detected potholes" />`;

    if (data.detections.length === 0) {
      table.innerHTML = `<div class="empty-state">No potholes detected in this image.</div>`;
    } else {
      table.innerHTML = data.detections.map((d, i) => `
        <div class="detection-row">
          <div>#${i + 1}</div>
          <div>bbox ${d.bbox.w}×${d.bbox.h}px @ (${d.bbox.x},${d.bbox.y})</div>
          <div><span class="badge badge-${d.severity.toLowerCase()}">${d.severity}</span></div>
          <div>${Math.round(d.confidence * 100)}%</div>
        </div>
      `).join("");
    }

    refreshStats();
  } catch (err) {
    resultArea.innerHTML = `<div class="empty-state" style="color:var(--high)">Could not reach backend: ${err.message}</div>`;
  } finally {
    detectBtn.disabled = false;
    detectBtn.textContent = "Start Detection";
  }
}

// ---------------- Dashboard stats ----------------
async function refreshStats() {
  try {
    const res = await fetch(API.stats);
    const data = await res.json();

    document.getElementById("statImages").textContent = data.images_processed;
    document.getElementById("statPotholes").textContent = data.total_potholes_detected;
    document.getElementById("statHigh").textContent = data.severity_totals.High;
    document.getElementById("statMedium").textContent = data.severity_totals.Medium;
    document.getElementById("statLow").textContent = data.severity_totals.Low;

    const histRes = await fetch(API.history);
    const hist = (await histRes.json()).history;
    const recentList = document.getElementById("recentList");

    if (hist.length === 0) {
      recentList.innerHTML = `<div class="empty-state">No detections yet. Head to <strong>Detect</strong> to scan a road image.</div>`;
    } else {
      recentList.innerHTML = hist.slice(0, 6).map(r => `
        <div class="recent-item">
          <div>
            <div class="rt-name">${r.filename}</div>
            <div class="rt-meta">${r.timestamp} · ${r.total_detections} detection(s)</div>
          </div>
          <div>${severityBadges(r.severity_counts)}</div>
        </div>
      `).join("");
    }
  } catch (e) { /* backend offline, ignore */ }
}

function severityBadges(counts) {
  let out = "";
  if (counts.High) out += `<span class="badge badge-high">${counts.High} High</span> `;
  if (counts.Medium) out += `<span class="badge badge-medium">${counts.Medium} Med</span> `;
  if (counts.Low) out += `<span class="badge badge-low">${counts.Low} Low</span>`;
  return out || `<span class="badge badge-low">clear</span>`;
}

// ---------------- History table ----------------
async function renderHistory() {
  const body = document.getElementById("historyBody");
  try {
    const res = await fetch(API.history);
    const hist = (await res.json()).history;

    if (hist.length === 0) {
      body.innerHTML = `<tr><td colspan="5" class="empty-state">No history yet.</td></tr>`;
      return;
    }

    body.innerHTML = hist.map(r => `
      <tr>
        <td style="font-family:var(--font-mono); color:var(--muted);">${r.id}</td>
        <td>${r.filename}</td>
        <td style="font-family:var(--font-mono); font-size:11px; color:var(--muted);">${r.timestamp}</td>
        <td>${r.total_detections}</td>
        <td class="severity-mix">${severityBadges(r.severity_counts)}</td>
      </tr>
    `).join("");
  } catch (e) {
    body.innerHTML = `<tr><td colspan="5" class="empty-state">Could not load history.</td></tr>`;
  }
}

document.getElementById("clearHistoryBtn").addEventListener("click", async () => {
  if (!confirm("Clear all detection history for this session?")) return;
  await fetch(API.history, { method: "DELETE" });
  renderHistory();
  refreshStats();
});

// ---------------- Map ----------------
async function renderMap() {
  const canvas = document.getElementById("mapCanvas");
  try {
    const res = await fetch(API.stats);
    const data = await res.json();

    if (!data.map_points || data.map_points.length === 0) {
      canvas.innerHTML = `<div class="empty-state">No geo-tagged detections yet.</div>`;
      return;
    }

    const lats = data.map_points.map(p => p.lat);
    const lngs = data.map_points.map(p => p.lng);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
    const latRange = (maxLat - minLat) || 0.001;
    const lngRange = (maxLng - minLng) || 0.001;

    const colorMap = { High: "var(--high)", Medium: "var(--medium)", Low: "var(--low)" };

    canvas.innerHTML = data.map_points.map(p => {
      const xPct = ((p.lng - minLng) / lngRange) * 84 + 8;
      const yPct = (1 - (p.lat - minLat) / latRange) * 84 + 8;
      return `<div class="map-point" style="left:${xPct}%; top:${yPct}%; background:${colorMap[p.severity]}; color:${colorMap[p.severity]};" title="${p.severity} · ${Math.round(p.confidence*100)}% confidence"></div>`;
    }).join("");
  } catch (e) {
    canvas.innerHTML = `<div class="empty-state">Could not load map data.</div>`;
  }
}

// ---------------- Init ----------------
checkHealth();
refreshStats();
setInterval(checkHealth, 15000);
