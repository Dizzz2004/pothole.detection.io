"""
detector.py
------------
Core detection engine for the Pothole Detection System.

Pipeline (matches the project's "Architectural Design" / "Algorithms Used" slides):

  1. Image Processing (candidate generation)
     - Grayscale conversion, blur, adaptive thresholding & Canny edge
       detection to isolate surface irregularities (dark, textured blobs)
       on the road surface.
     - Morphological closing to merge fragmented edges into solid regions.
     - Contour extraction -> candidate bounding boxes.

  2. Feature Extraction (per candidate region)
     - Area, circularity, aspect ratio
     - Mean darkness relative to surrounding road surface
     - Texture roughness (variance of Laplacian - detects irregular,
       broken surfaces vs. smooth road / shadows)

  3. Machine Learning Classification
     - A RandomForestClassifier (scikit-learn) filters true potholes from
       false positives (shadows, tar patches, lane markings, debris).
     - NOTE: This ships trained on synthetically generated, rule-labeled
       feature data so the demo works out-of-the-box with zero external
       downloads. For production accuracy, retrain `train_classifier()`
       on real labelled data (e.g. the Kaggle Pothole Image Dataset
       referenced in the project report) or swap this stage for a CNN /
       YOLOv8 model trained on annotated pothole images.

  4. Severity Classification
     - Detected potholes are bucketed into Low / Medium / High severity
       based on their real-world estimated area.

  5. GPS tagging (simulated)
     - Since this demo runs on uploaded static images, GPS coordinates
       are simulated per-detection. In the real vehicle-mounted system
       (see architecture diagram), these come from the device's GPS
       module at capture time.
"""

import io
import os
import random
import time
import base64
import pickle

import cv2
import numpy as np
from sklearn.ensemble import RandomForestClassifier

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "pothole_rf.pkl")


# --------------------------------------------------------------------------
# 1. Feature extraction
# --------------------------------------------------------------------------
def extract_features(gray_img, mask_roi, x, y, w, h, image_area):
    """Compute a small, interpretable feature vector for a candidate region."""
    roi = gray_img[y:y + h, x:x + w]
    if roi.size == 0:
        return None

    # Darkness: potholes are usually darker than surrounding tarmac
    mean_intensity = float(np.mean(roi))

    # Texture roughness via variance of Laplacian (broken surface = high variance)
    laplacian_var = float(cv2.Laplacian(roi, cv2.CV_64F).var())

    # Shape descriptors
    contour_area = float(cv2.contourArea(mask_roi)) if mask_roi is not None else float(w * h)
    rect_area = float(w * h)
    extent = contour_area / rect_area if rect_area > 0 else 0
    aspect_ratio = w / float(h) if h > 0 else 0

    perimeter = cv2.arcLength(mask_roi, True) if mask_roi is not None else 0
    circularity = (4 * np.pi * contour_area / (perimeter ** 2)) if perimeter > 0 else 0

    area_ratio = rect_area / image_area  # relative size within the frame

    return np.array([
        mean_intensity,
        laplacian_var,
        extent,
        aspect_ratio,
        circularity,
        area_ratio,
    ])


FEATURE_NAMES = [
    "mean_intensity", "laplacian_var", "extent",
    "aspect_ratio", "circularity", "area_ratio",
]


# --------------------------------------------------------------------------
# 2. Synthetic training data + RandomForest classifier
#    (rule-labelled, so the demo is fully self-contained / offline)
# --------------------------------------------------------------------------
def _generate_synthetic_dataset(n=2000, seed=42):
    rng = np.random.default_rng(seed)
    X, y = [], []

    for _ in range(n):
        is_pothole = rng.random() < 0.5
        if is_pothole:
            mean_intensity = rng.normal(60, 15)      # dark
            laplacian_var = rng.normal(650, 180)      # rough / irregular texture
            extent = rng.normal(0.72, 0.1)             # fills its bounding box fairly well
            aspect_ratio = rng.normal(1.1, 0.35)        # roughly round/blobby
            circularity = rng.normal(0.65, 0.15)
            area_ratio = abs(rng.normal(0.01, 0.015)) + 0.0008
        else:
            mean_intensity = rng.normal(130, 30)       # brighter (road / shadow edge / marking)
            laplacian_var = rng.normal(180, 90)         # smoother texture
            extent = rng.normal(0.45, 0.2)
            aspect_ratio = rng.normal(2.2, 1.2)          # elongated (cracks/lines/shadows)
            circularity = rng.normal(0.25, 0.15)
            area_ratio = abs(rng.normal(0.002, 0.004)) + 0.00005

        X.append([mean_intensity, laplacian_var, extent, aspect_ratio, circularity, area_ratio])
        y.append(1 if is_pothole else 0)

    return np.array(X), np.array(y)


def train_classifier():
    X, y = _generate_synthetic_dataset()
    clf = RandomForestClassifier(
        n_estimators=150, max_depth=8, random_state=42, class_weight="balanced"
    )
    clf.fit(X, y)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    return clf


def load_or_train_classifier():
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return train_classifier()


_CLASSIFIER = load_or_train_classifier()


# --------------------------------------------------------------------------
# 3. Severity classification
# --------------------------------------------------------------------------
def classify_severity(area_ratio):
    """Bucket a detection into Low / Medium / High severity by relative size."""
    if area_ratio < 0.004:
        return "Low"
    elif area_ratio < 0.015:
        return "Medium"
    return "High"


SEVERITY_COLOR = {
    "Low": (0, 200, 0),       # green (BGR)
    "Medium": (0, 165, 255),  # orange
    "High": (0, 0, 255),      # red
}


# --------------------------------------------------------------------------
# 4. Main detection pipeline
# --------------------------------------------------------------------------
def detect_potholes(image_bytes, confidence_threshold=0.55, base_lat=12.9716, base_lng=77.5946):
    """
    Run the full detection pipeline on raw image bytes.

    Returns a dict with:
      - annotated_image_base64: JPEG image with bounding boxes drawn
      - detections: list of {bbox, severity, confidence, lat, lng, area_px}
      - stats: summary counts
    """
    file_bytes = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image. Please upload a valid JPG/PNG file.")

    orig_h, orig_w = img.shape[:2]
    image_area = float(orig_h * orig_w)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # Adaptive threshold highlights locally dark, irregular regions
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 25, 8
    )

    # Canny edges catch the broken/cracked boundary of a pothole
    edges = cv2.Canny(blurred, 40, 130)

    combined = cv2.bitwise_or(thresh, edges)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    closed = cv2.dilate(closed, kernel, iterations=1)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = max(image_area * 0.0006, 150)   # ignore tiny noise
    max_area = image_area * 0.35               # ignore near-full-frame blobs

    detections = []
    rng = random.Random(42)

    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(c)
        feats = extract_features(gray, c, x, y, w, h, image_area)
        if feats is None:
            continue

        proba = _CLASSIFIER.predict_proba(feats.reshape(1, -1))[0][1]
        if proba < confidence_threshold:
            continue

        area_ratio = (w * h) / image_area
        severity = classify_severity(area_ratio)

        # Simulated GPS jitter around a base coordinate (Bengaluru by default)
        lat = base_lat + rng.uniform(-0.01, 0.01)
        lng = base_lng + rng.uniform(-0.01, 0.01)

        detections.append({
            "bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
            "confidence": round(float(proba), 3),
            "severity": severity,
            "area_px": int(area),
            "lat": round(lat, 6),
            "lng": round(lng, 6),
        })

    # Non-max suppression to remove overlapping duplicate boxes
    detections = _suppress_overlaps(detections)

    # Draw annotations
    annotated = img.copy()
    for i, det in enumerate(detections, start=1):
        b = det["bbox"]
        color = SEVERITY_COLOR[det["severity"]]
        cv2.rectangle(annotated, (b["x"], b["y"]), (b["x"] + b["w"], b["y"] + b["h"]), color, 3)
        label = f"#{i} {det['severity']} {int(det['confidence']*100)}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(annotated, (b["x"], b["y"] - th - 10), (b["x"] + tw + 6, b["y"]), color, -1)
        cv2.putText(annotated, label, (b["x"] + 3, b["y"] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

    ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    annotated_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    severity_counts = {"Low": 0, "Medium": 0, "High": 0}
    for d in detections:
        severity_counts[d["severity"]] += 1

    return {
        "annotated_image_base64": annotated_b64,
        "detections": detections,
        "stats": {
            "total_detections": len(detections),
            "severity_counts": severity_counts,
            "image_size": {"width": orig_w, "height": orig_h},
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


def _suppress_overlaps(detections, iou_thresh=0.35):
    """Simple greedy NMS on our own detection dicts, sorted by confidence."""
    if not detections:
        return []

    detections = sorted(detections, key=lambda d: d["confidence"], reverse=True)
    kept = []

    def iou(a, b):
        ax1, ay1 = a["x"], a["y"]
        ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
        bx1, by1 = b["x"], b["y"]
        bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]

        inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
        inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
        inter_w, inter_h = max(0, inter_x2 - inter_x1), max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        union = area_a + area_b - inter_area
        return inter_area / union if union > 0 else 0

    for det in detections:
        overlap = False
        for k in kept:
            if iou(det["bbox"], k["bbox"]) > iou_thresh:
                overlap = True
                break
        if not overlap:
            kept.append(det)

    return kept
