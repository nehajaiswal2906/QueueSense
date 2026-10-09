# QueueSense - Computer Vision Intelligence Subsystem

QueueSense is a real-time computer vision queue intelligence system designed for college canteen queue monitoring.

This subsystem handles:
1. **YOLO Person Detection**: Pretrained YOLOv8n (COCO class 0).
2. **Multi-Object Tracking**: ByteTrack tracker for consistent person ID persistence across frames.
3. **Queue ROI Logic**: Point-in-polygon evaluation using the bottom-center of bounding boxes (foot ground position).
4. **Queue Counting**: Real-time count of people actively standing within the queue region.
5. **Service Rate Estimation**: Measures departures after queue dwell (`service_rate = people_leaving / elapsed_minutes`).
6. **Backend Contract Output**: Standardized JSON / dictionary contract for Team B's Flask backend.
7. **Visual Debugger**: Real-time HUD displaying bounding boxes (green in-queue, cyan outside), IDs, ROI polygon, and live stats.

---

## 1. Quick Setup

```bash
pip install -r requirements.txt
```

Dependencies:
- `ultralytics>=8.0.0`
- `opencv-python>=4.8.0`
- `numpy>=1.24.0`
- `lap>=0.5.12`

Pretrained model weights (`yolov8n.pt`, ~6.2 MB) are auto-cached on first run.

---

## 2. Quick Start & Demo

### Run on a video file with live visual debug window:
```bash
python run_demo.py --video sample_test.mp4
```

### Run headless and save output video:
```bash
python run_demo.py --video sample_test.mp4 --save output_demo.mp4 --no-window
```

### Run on live webcam:
```bash
python run_demo.py --cam 0
```

---

## 3. Team B (Flask Backend) Integration

Team B can import the pipeline directly:

```python
from pipeline import create_pipeline

# 1. Initialize pipeline with your venue's queue polygon:
QUEUE_ROI = [
    (100, 100),
    (600, 100),
    (600, 600),
    (100, 600)
]
pipeline = create_pipeline(roi_polygon=QUEUE_ROI, conf_thresh=0.35)

# 2. Process any frame from camera/stream:
result = pipeline.process_frame(frame)
```

### Contract Schema:
```json
{
  "people": [
    {
      "id": 12,
      "bbox": [150, 120, 220, 300],
      "confidence": 0.91,
      "in_queue": true
    }
  ],
  "queue_count": 1,
  "service_rate": 2.5
}
```

---

## 4. Test Suites

### Edge Case Verification (8 Critical Edge Cases):
```bash
python -m unittest tests/test_edge_cases.py
```
Covers:
1. No people (empty scene).
2. One person (inside vs outside ROI).
3. Multiple people simultaneously.
4. Person entering queue.
5. Person leaving queue & service rate calculation.
6. Overlapping / occluded persons.
7. Person outside ROI.
8. Low-quality / shaky video.

### Multi-Scenario Benchmarking:
```bash
python tests/test_scenarios.py
```
Tests on 3 diverse video streams:
- `sample_test.mp4`: Outdoor walkway / pedestrian flow
- `people_detection.mp4`: Entrance corridor with crossing pedestrians
- `classroom.mp4`: Indoor crowded room

---

## 5. Documented Limitations & Edge Case Handling

1. **Severe Occlusion**: If a person is completely hidden behind another person for multiple seconds, ByteTrack may assign a new track ID when they re-emerge.
2. **Camera Perspective**: The bottom-center of the bounding box is used as the foot position. Severe overhead angles or extreme side angles may require tweaking the ROI polygon vertices.
3. **Short Dwell vs Service**: To prevent false service counts from passers-by momentarily stepping onto the ROI edge, the system enforces `min_dwell_frames` (default: 5 frames) before a departure is counted as a served customer.
4. **Initial Warmup Period**: During the first ~3 seconds of observation, service rate defaults to 0.00 until sufficient observation time has elapsed to compute a statistically meaningful rate.

## 5. Running the Team B Flask Backend

From the repository root, create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

Start the Flask backend from the repository root:

```bash
python -m backend.app
```

The backend provides these endpoints:

* `GET /` — confirms the backend is running.
* `GET /health` — health check.
* `GET /mock` — sample queue analysis.
* `POST /analyze` — analyze queue count and service rate supplied as JSON.
* `POST /upload` — upload an image or video for CV analysis.

The first run may download the YOLO model weights. Internet access is required if the weights are not already cached.

For local testing, use Flask's test client or send requests to the running server.
