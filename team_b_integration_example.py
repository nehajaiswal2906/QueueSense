"""
QueueSense - Team B (Flask Backend) Integration Example
Demonstrates how Team B imports, consumes, and serializes output from the CV pipeline,
including real-frame person detection, safe wait-time calculation, and session resetting.
"""

import json
import os
import cv2
import numpy as np

from pipeline import create_pipeline, QueueSensePipeline

# ------------------------------------------------------------------------------
# 1. Pipeline Initialization (Run once on Flask server startup)
# ------------------------------------------------------------------------------
# Configure polygonal queue ROI matching the venue camera's ground perspective:
QUEUE_ROI = [
    (100, 50),
    (600, 50),
    (600, 400),
    (100, 400)
]

# Optional service / counter area (where served customers step up)
SERVICE_ZONE = [
    (550, 50),
    (750, 50),
    (750, 350),
    (550, 350)
]

# Initialize pipeline (Team B can also supply a fallback manual_service_rate in people/min)
pipeline = create_pipeline(
    roi_polygon=QUEUE_ROI,
    service_zone=SERVICE_ZONE,
    conf_thresh=0.35,
    manual_service_rate=2.0  # Demonstrating fallback service rate: 2.0 people/min
)

print(f"[Team B Init] Pipeline initialized on device: {pipeline.device.upper()}")


# ------------------------------------------------------------------------------
# 2. Reading a Real Video Frame with Visible People
# ------------------------------------------------------------------------------
# Find an available video source with active pedestrian / queue activity
video_candidates = [
    ("people_detection.mp4", 35),  # Frame 35 has an active pedestrian inside ROI
    ("sample_test.mp4", 70),       # Frame 70 has an active pedestrian
    ("classroom.mp4", 10)          # Frame 10 has multiple people
]

frame = None
source_name = "Synthetic Frame"

for vid_path, target_frame in video_candidates:
    if os.path.exists(vid_path):
        cap = cv2.VideoCapture(vid_path)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, captured_frame = cap.read()
            cap.release()
            if ret and captured_frame is not None:
                frame = captured_frame
                source_name = f"{vid_path} (frame {target_frame})"
                break

if frame is None:
    if os.path.exists("test_bus.jpg"):
        frame = cv2.imread("test_bus.jpg")
        source_name = "test_bus.jpg"
    else:
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

print(f"[Team B Input] Successfully loaded test frame from: {source_name}")

# ------------------------------------------------------------------------------
# 3. Process the Frame through the CV Pipeline
# ------------------------------------------------------------------------------
result = pipeline.process_frame(frame)

print("\n" + "=" * 60)
print("[TEAM B OUTPUT CONTRACT RESULT — REAL FRAME PROCESSING]")
print("=" * 60)
print(f"Queue Count   : {result['queue_count']} people")
print(f"Total Served  : {result['total_served']} people")
print(f"Service Rate  : {result['service_rate']} people/min")
print(f"Tracked People: {len(result['people'])}")

for p in result["people"]:
    print(f"  - ID: {p['id']}, BBox: {p['bbox']}, In-Queue: {p['in_queue']}, Conf: {p['confidence']}")

# ------------------------------------------------------------------------------
# 4. Safe Wait-Time Calculation (Zero / None Division Handling for Team B)
# ------------------------------------------------------------------------------
# Team B calculates wait time as: queue_count / service_rate
# Safe guard: NEVER divide by None or 0.0
if result["service_rate"] is not None and result["service_rate"] > 0:
    est_wait_minutes = round(result["queue_count"] / result["service_rate"], 1)
    print(f"\nCalculated Wait Time: ~{est_wait_minutes} minutes")
else:
    est_wait_minutes = None
    print("\nCalculated Wait Time: Unavailable (Cannot compute without valid service rate)")

# ------------------------------------------------------------------------------
# 5. JSON Serialization Check (Ensures Flask jsonify / json.dumps compatibility)
# ------------------------------------------------------------------------------
json_payload = json.dumps({
    **result,
    "estimated_wait_time_minutes": est_wait_minutes
}, indent=2)
print(f"\n[Serialized JSON for HTTP Response]:\n{json_payload}")

# ------------------------------------------------------------------------------
# 6. Resetting the Pipeline (For independent sessions or video restart)
# ------------------------------------------------------------------------------
pipeline.reset()
print("\n[Team B Session] Pipeline tracker and analyzer reset successfully.")


# ------------------------------------------------------------------------------
# 7. Flask Blueprint / Route Example (Ready for Team B to copy into server.py)
# ------------------------------------------------------------------------------
"""
from flask import Flask, jsonify
import cv2
from pipeline import create_pipeline

app = Flask(__name__)
pipeline = create_pipeline(roi_polygon=QUEUE_ROI, service_zone=SERVICE_ZONE)
camera = cv2.VideoCapture(0)

@app.route('/api/queue-status', methods=['GET'])
def get_queue_status():
    success, frame = camera.read()
    if not success or frame is None:
        return jsonify({"error": "Failed to capture camera frame"}), 503

    cv_data = pipeline.process_frame(frame)

    # Team B Wait-Time Logic (safe against None and zero):
    wait_time = None
    if cv_data["service_rate"] and cv_data["service_rate"] > 0:
        wait_time = round(cv_data["queue_count"] / cv_data["service_rate"], 1)

    response = {
        "status": "success",
        "data": {
            **cv_data,
            "estimated_wait_minutes": wait_time
        }
    }
    return jsonify(response), 200

@app.route('/api/reset-session', methods=['POST'])
def reset_session():
    pipeline.reset()
    return jsonify({"status": "session_reset"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
"""
