"""
QueueSense - Team B (Flask Backend) Integration Example
Shows how Team B imports and consumes the CV pipeline.
"""

import cv2
from pipeline import QueueSensePipeline, create_pipeline

# -------------------------------------------------------------
# 1. Pipeline Initialization (Run once on Flask server startup)
# -------------------------------------------------------------
# You can customize the ROI polygon coordinates to match your canteen camera view:
QUEUE_ROI = [
    (100, 100),
    (600, 100),
    (600, 600),
    (100, 600)
]

# Initialize pipeline instance
pipeline = create_pipeline(roi_polygon=QUEUE_ROI, conf_thresh=0.35)

print("Pipeline initialized successfully.")


# -------------------------------------------------------------
# 2. Processing a single frame (e.g. from camera or video stream)
# -------------------------------------------------------------
# Read a frame using OpenCV (or decode from multipart/bytes)
cap = cv2.VideoCapture("sample_test.mp4")
ret, frame = cap.read()
cap.release()

if ret:
    # Process the frame through the CV pipeline
    result = pipeline.process_frame(frame)

    print("\n[Sample Contract Output for Flask API]:")
    print(result)

    # Access fields directly:
    print(f"\nCurrent Queue Count : {result['queue_count']}")
    print(f"Current Service Rate: {result['service_rate']} people/min")
    print(f"Tracked People Count: {len(result['people'])}")

    for person in result["people"]:
        print(
            f" - Person ID: {person['id']}, "
            f"BBox: {person['bbox']}, "
            f"In Queue: {person['in_queue']}, "
            f"Conf: {person['confidence']}"
        )

# -------------------------------------------------------------
# 3. How to use inside a Flask route:
# -------------------------------------------------------------
"""
from flask import Flask, jsonify
app = Flask(__name__)

pipeline = create_pipeline(roi_polygon=QUEUE_ROI)

@app.route('/api/queue-status', methods=['GET'])
def get_queue_status():
    # Capture latest frame from camera
    success, frame = camera.read()
    if not success:
        return jsonify({"error": "Failed to read camera frame"}), 500
        
    data = pipeline.process_frame(frame)
    return jsonify(data)
"""
