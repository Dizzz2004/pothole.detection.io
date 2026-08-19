# Road Guardian — Pothole Detection System

A full-stack implementation of the **"Detection of Potholes"** mini-project:
a Flask + OpenCV + scikit-learn backend, and a browser dashboard front end
(styled after the "Road Guardian" app mockups in the project report).

Upload a road-surface photo → the system detects potholes, classifies their
severity (Low / Medium / High), geo-tags them, and logs everything to a
live dashboard, map, and history view.

---

## 1. What's inside

```
pothole-detection-app/
└── backend/
    ├── app.py              # Flask server: routes + in-memory detection DB
    ├── detector.py         # Detection pipeline (OpenCV + RandomForest ML)
    ├── requirements.txt
    ├── model/
    │   └── pothole_rf.pkl  # trained classifier (auto-generated on first run)
    ├── templates/
    │   └── index.html      # dashboard UI
    ├── static/
    │   ├── style.css
    │   └── script.js
    └── uploads/             # (scratch folder, currently unused by default)
```

## 2. How detection works

This mirrors the pipeline described in the "Architectural Design" and
"Algorithms Used" slides of the report:

1. **Image processing (candidate generation)** — grayscale conversion,
   adaptive thresholding, and Canny edge detection isolate dark, irregular
   surface regions; morphological closing merges broken edges into solid
   blobs; contours become candidate bounding boxes.
2. **Feature extraction** — for each candidate: darkness, texture
   roughness (Laplacian variance), how much of its bounding box it fills,
   aspect ratio, circularity, and relative size.
3. **Machine learning classification** — a `RandomForestClassifier`
   (scikit-learn) scores each candidate as pothole / not-pothole, filtering
   out shadows, cracks, tar patches, and lane markings.
4. **Severity classification** — surviving detections are bucketed into
   Low / Medium / High based on their real-world area.
5. **Geo-tagging** — each detection gets a simulated GPS coordinate (in the
   real vehicle-mounted system from the report's architecture diagram,
   this comes from the device's GPS module at capture time).

> **Note on the ML model:** to keep this project fully self-contained and
> runnable offline with zero downloads, the RandomForest classifier ships
> trained on synthetically generated, rule-labeled feature data — it
> already reliably tells "dark irregular blob" candidates apart from
> "light/elongated" false positives (shadows, lines, cracks). For
> production-grade accuracy on real photos, retrain it on a labeled dataset
> such as the **Kaggle Pothole Image Dataset** referenced in the report, or
> swap the classification stage for a CNN / YOLOv8 model trained on
> annotated pothole images — the rest of the pipeline (API, dashboard,
> severity logic, map, history) needs no changes to support that.

## 3. Setup & run

Requires Python 3.9+.

```bash
cd pothole-detection-app/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The first request will train and cache the RandomForest classifier
(`model/pothole_rf.pkl`) — this takes under a second.

## 4. Using the app

- **Dashboard** — live counts of images processed, potholes detected, and
  severity breakdown, plus a feed of recent detections.
- **Detect** — drag & drop (or click to browse) a road-surface photo, adjust
  the sensitivity slider if needed, and run detection. The annotated image
  and a per-pothole table (bounding box, severity, confidence) are shown.
- **Map** — a lightweight geo-scatter of every detection logged this
  session, color-coded by severity.
- **History** — a table of every scan run this session, with a button to
  clear it.

## 5. API reference

| Method | Endpoint         | Description                                   |
|--------|------------------|------------------------------------------------|
| GET    | `/`              | Dashboard UI                                   |
| POST   | `/api/detect`    | Upload `image` (multipart/form-data); optional `?confidence=0.55` query param. Returns annotated image (base64) + detections + stats. |
| GET    | `/api/history`   | List of all detections run this session        |
| DELETE | `/api/history`   | Clear session history                          |
| GET    | `/api/stats`     | Dashboard summary stats + map points            |
| GET    | `/api/health`    | Backend health check                            |

Example `curl`:

```bash
curl -X POST -F "image=@road.jpg" "http://127.0.0.1:5000/api/detect?confidence=0.55"
```

## 6. Extending this into the full system from the report

The report's architecture also covers a mobile volunteer-capture app,
Firebase storage, a `.tflite` mobile model, and a Google-Maps-based public
map. This project implements the **core detection engine and web
dashboard** in a runnable form. Natural next steps to reach full parity:

- Swap the RandomForest stage for a CNN (e.g. train a MobileNet/YOLO model
  on the Kaggle dataset) and export to `.tflite` for the mobile app.
- Replace the in-memory `DETECTION_HISTORY` list in `app.py` with a real
  database (SQLite/Postgres/Firebase) for persistence across restarts.
- Wire the "Map" view to the Google Maps JavaScript API using real GPS
  coordinates from a mobile client instead of simulated jitter.
- Add authentication for the volunteer-contribution flow shown in the
  architecture diagram.
