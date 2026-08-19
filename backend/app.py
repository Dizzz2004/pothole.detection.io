"""
app.py
------
Flask backend for the "Road Guardian" Pothole Detection System.

Run with:  python app.py
Then open: http://127.0.0.1:5000

Endpoints:
  GET  /                    -> frontend dashboard (templates/index.html)
  POST /api/detect          -> upload an image, run detection, get results
  GET  /api/history         -> list of all past detections (this session)
  GET  /api/stats           -> dashboard summary stats
  DELETE /api/history       -> clear history
"""

import os
import uuid
import time

from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

from detector import detect_potholes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload cap

# In-memory "database" (Road Guardian's Firebase/Database layer, simplified
# for this demo). Swap for a real DB (SQLite/Postgres/Firebase) in production.
DETECTION_HISTORY = []


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/detect", methods=["POST"])
def api_detect():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided (field name must be 'image')."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Unsupported file type. Allowed: {sorted(ALLOWED_EXTENSIONS)}"}), 400

    try:
        confidence = float(request.args.get("confidence", 0.55))
        confidence = min(max(confidence, 0.1), 0.95)
        image_bytes = file.read()
        result = detect_potholes(image_bytes, confidence_threshold=confidence)
    except Exception as e:
        return jsonify({"error": f"Detection failed: {str(e)}"}), 500

    record = {
        "id": str(uuid.uuid4())[:8],
        "filename": secure_filename(file.filename),
        "timestamp": result["stats"]["processed_at"],
        "total_detections": result["stats"]["total_detections"],
        "severity_counts": result["stats"]["severity_counts"],
        "detections": result["detections"],
    }
    DETECTION_HISTORY.insert(0, record)

    return jsonify({
        "record_id": record["id"],
        "annotated_image_base64": result["annotated_image_base64"],
        "detections": result["detections"],
        "stats": result["stats"],
    })


@app.route("/api/history", methods=["GET"])
def api_history():
    return jsonify({"history": DETECTION_HISTORY})


@app.route("/api/history", methods=["DELETE"])
def api_clear_history():
    DETECTION_HISTORY.clear()
    return jsonify({"message": "History cleared."})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    total_images = len(DETECTION_HISTORY)
    total_potholes = sum(r["total_detections"] for r in DETECTION_HISTORY)
    severity_totals = {"Low": 0, "Medium": 0, "High": 0}
    for r in DETECTION_HISTORY:
        for k, v in r["severity_counts"].items():
            severity_totals[k] += v

    all_points = []
    for r in DETECTION_HISTORY:
        for d in r["detections"]:
            all_points.append({
                "lat": d["lat"], "lng": d["lng"],
                "severity": d["severity"], "confidence": d["confidence"],
            })

    return jsonify({
        "images_processed": total_images,
        "total_potholes_detected": total_potholes,
        "severity_totals": severity_totals,
        "map_points": all_points,
    })


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok", "time": time.strftime("%Y-%m-%d %H:%M:%S")})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
