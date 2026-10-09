# QueueSense — Computer Vision Pipeline (Team A)

QueueSense is an AI-powered queue intelligence system designed for college canteen queue monitoring. 

**Team A Scope**: Team A owns the computer-vision pipeline, queue occupancy counting, service-event tracking, and the Python integration interface for Team B (Flask Backend). Frontend, database, authentication, and backend wait-time prediction logic are handled separately by Teams B and C.

---

## 1. System Architecture & Pipeline

```text
Camera / Video Input (.mp4 / stream)
                 │
                 ▼
       YOLOv8 Nano (yolov8n.pt)
    [COCO Class 0: Person Detection]
                 │
                 ▼
        ByteTrack Algorithm
    [Multi-Object Tracking across Frames]
                 │
                 ▼
     Polygonal Queue ROI Logic
 [cv2.pointPolygonTest on Foot Position]
                 │
                 ├──▶ Queue Count (Active queue occupancy)
                 │
                 ▼
     Service Zone & Dwell Tracker
[min_dwell_frames + counter zone entry]
                 │
                 ├──▶ Total Served & Service Rate (people/min or None)
                 │
                 ▼
   JSON-Serializable Output Contract
                 │
                 ▼
      Team B Flask Backend Integration
```

---

## 2. File Responsibilities

| File | Responsibility |
| :--- | :--- |
| `config.py` | Central configuration: default ROI polygons, model weights, confidence thresholds, dwell thresholds, and observation timers. |
| `detector.py` | YOLOv8n inference filtered strictly for class 0 (person), ByteTrack multi-object tracking, device selection (CPU/CUDA), and session reset. |
| `queue_analyzer.py` | Polygonal ROI point-in-polygon calculations, foot bottom-center positioning, service-zone event verification, dwell-time filtering, bounded track memory, and service-rate calculation. |
| `pipeline.py` | Unified high-level pipeline integrating detector, analyzer, and visualizer. Implements `process_frame()`, `reset()`, and `create_pipeline()` factory. |
| `debug_visualizer.py` | Renders visual overlays: green/amber bounding boxes, tracking IDs, foot position dots, queue polygon, service counter zone, and real-time HUD monitor. |
| `run_demo.py` | CLI demo runner supporting local video, webcam, headless execution, frame limiting, annotated video recording, and validation summary. |
| `team_b_integration_example.py` | Standalone reference implementation demonstrating how Team B imports the pipeline, processes frames, serializes JSON, avoids division-by-zero, and resets sessions. |
| `tests/test_edge_cases.py` | Fast unit test suite covering all 17 critical queue logic edge cases with synthetic detections (runs in <0.1s without GPU). |
| `tests/test_scenarios.py` | Integration test suite executing the full vision pipeline on 3 real video scenarios. |
| `test_phase1_2.py` | Verification script validating YOLO detection and ByteTrack ID continuity on consecutive video frames. |
| `requirements.txt` | Minimal Python package dependencies. |

---

## 3. Prerequisites & Windows Setup

### Recommended Environment: Python 3.10 – 3.14 on Windows 10/11
The pipeline runs on standard CPU. CUDA acceleration is automatically used if a compatible NVIDIA GPU and PyTorch CUDA build are detected.

### Setup using Windows PowerShell:
```powershell
# 1. Clone repository and navigate to project folder
cd "c:\Users\njneh\OneDrive\Desktop\My_AIML_Journey\Hackathon\Hackathon_02\QueueSense\QueueSense"

# 2. (Optional) Create and activate a clean virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install required packages
python -m pip install -r requirements.txt
```

### Pretrained Model Weights:
The system uses the lightweight official YOLOv8 nano model (`yolov8n.pt`, ~6.2 MB). If not present locally, it is automatically cached by Ultralytics upon initial execution.

---

## 4. Running the Video Demo

### A. Run Headless & Save Verified Annotated Video (Fastest & Headless):
```powershell
python run_demo.py --video people_detection.mp4 --save output_verified.mp4 --no-window --max-frames 60
```

### B. Run Interactive Visual Window (GUI):
```powershell
python run_demo.py --video sample_test.mp4
```
*(Press `q` or `Esc` in the OpenCV window to exit).*

### C. Run on Live Webcam:
```powershell
python run_demo.py --cam 0
```

### Supported CLI Options:
- `--video <path>`: Input video file path (default: `sample_test.mp4`).
- `--cam <index>`: Webcam device index (e.g. `0`).
- `--save <path>`: Destination path for annotated MP4 video.
- `--no-window`: Runs headless (recommended for servers and automated tests).
- `--max-frames <N>`: Limits execution to `N` frames.
- `--conf <float>`: Confidence threshold for YOLO detection (default: `0.35`).
- `--manual-rate <float>`: Optional fallback service rate in people/min when automated data is pending.

---

## 5. Configuring the Queue ROI & Service Counter

Coordinates are configured in pixel space `(x, y)` corresponding to camera frame dimensions:

```python
from pipeline import create_pipeline

# Define polygonal Queue Region of Interest (ROI)
# Represents where waiting customers stand in the canteen
QUEUE_ROI = [
    (100, 100),  # Top-left
    (600, 100),  # Top-right
    (600, 600),  # Bottom-right
    (100, 600)   # Bottom-left
]

# (Optional) Service Counter Zone
# Represents the pickup/billing counter where customers receive their order
SERVICE_ZONE = [
    (550, 100),
    (750, 100),
    (750, 350),
    (550, 350)
]

pipeline = create_pipeline(roi_polygon=QUEUE_ROI, service_zone=SERVICE_ZONE)
```

### Foot-Position Ground Anchor:
To eliminate perspective distortion, a person is determined to be inside or outside the queue based on their **bottom-center coordinate** `((x1 + x2) // 2, y2)`. This represents the customer's feet on the ground floor rather than their head or torso.

---

## 6. Service-Rate Estimation Logic & Safety Fallback

### How Service Events are Counted:
A customer is counted as served **only** when all of the following conditions are met:
1. The person has a consistent tracking ID (`id >= 0`).
2. The person dwelled inside the queue ROI for at least `min_dwell_frames` (default: 5 frames), proving they were an active queue participant.
3. The person transitioned into the designated `service_zone` (counter area).
4. The person has not already been counted (`served_ids` set prevents double-counting).

### What is NOT Counted as Service:
- **Passersby**: Walking through the area without dwelling (< `min_dwell_frames`) is ignored.
- **Queue Abandonment**: Stepping out of the queue away from the counter is **not** counted as served.
- **Occlusions / Dropped Tracks**: A person temporarily obscured behind a pillar or another customer is **never** assumed served.

### Safe Service-Rate Publication:
- `service_rate = total_served / elapsed_minutes` (in people per minute).
- When fewer than 1 person has been served or observation time is below `min_observation_seconds` (5.0s), `service_rate` is returned as `None` (JSON `null`).
- Team B must inspect `if result["service_rate"] is not None and result["service_rate"] > 0:` to prevent divide-by-zero crashes.
- If automated service detection is not suitable for a camera angle, `manual_service_rate` (e.g. `2.0` people/min) can be passed as a static fallback.

---

## 7. Team B Integration Contract

Team B imports `pipeline.py` directly into Flask:

```python
from pipeline import create_pipeline

pipeline = create_pipeline(roi_polygon=QUEUE_ROI, service_zone=SERVICE_ZONE)

# Process frame captured from OpenCV camera
result = pipeline.process_frame(frame)
```

### Output JSON Schema:
```json
{
  "people": [
    {
      "id": 1,
      "bbox": [272, 112, 455, 364],
      "confidence": 0.895,
      "in_queue": true
    }
  ],
  "queue_count": 1,
  "service_rate": null,
  "total_served": 0
}
```

### Contract Fields:
- `people` (`list`): Tracked person detections for the current frame.
  - `id` (`int`): Tracking ID (persistent across frames; `-1` if unassigned).
  - `bbox` (`list` of 4 `int`s): `[x1, y1, x2, y2]` coordinates.
  - `confidence` (`float`): Detection confidence between `0.0` and `1.0`.
  - `in_queue` (`bool`): `true` if bottom-center is inside the configured queue ROI.
- `queue_count` (`int`): Number of people currently detected inside the queue ROI.
- `service_rate` (`float` or `null`): People served per minute. Returned as `null` when insufficient evidence is available.
- `total_served` (`int`): Cumulative count of verified customer service events.

### Session Reset:
```python
pipeline.reset()  # Clears tracker state, dwell history, and service counts for a new session
```

---

## 8. Test Execution & Verified Results

### A. Fast Synthetic Unit Tests (17 Test Scenarios):
```powershell
python -m unittest tests/test_edge_cases.py
```
**Result**: **17 / 17 PASSED** in 0.067s.
Covers:
1. Empty scene (`queue_count = 0`).
2. Single person inside ROI.
3. Single person outside ROI.
4. Multiple people inside and outside simultaneously.
5. Person entering queue.
6. Person leaving queue without being falsely marked as served.
7. Valid service event counted exactly once.
8. Temporary occlusion not counting as service.
9. Missing/negative tracking ID handling.
10. Person re-entering queue.
11. Dwell-time threshold validation.
12. Session reset isolation.
13. Corrupt/empty/None frame handling.
14. Contract fields and types.
15. Full JSON serialization.
16. Safe `None` service rate handling and manual fallback.
17. Invalid polygon coordinate validation.

### B. Real-Video Integration Tests (3 Scenarios):
```powershell
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
