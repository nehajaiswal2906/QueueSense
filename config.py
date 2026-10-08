"""
QueueSense Configuration
Defines default parameters, ROI coordinates, model choice, and thresholds.
"""

from typing import List, Tuple

# Default Region of Interest (Polygon vertices in (x, y) coordinates)
# Adjust these coordinates to match the camera angle / queue area of the venue.
DEFAULT_QUEUE_ROI: List[Tuple[int, int]] = [
    (100, 100),
    (600, 100),
    (600, 600),
    (100, 600)
]

# Model settings
MODEL_PATH: str = "yolov8n.pt"  # Lightweight pretrained YOLOv8 nano
CONFIDENCE_THRESHOLD: float = 0.35  # Confidence threshold for person detection
TRACKER_TYPE: str = "bytetrack.yaml"

# Queue analysis parameters
MIN_QUEUE_DWELL_FRAMES: int = 5  # Minimum frames inside ROI before counting departure as served
LOST_TRACK_EXPIRY_SECONDS: float = 2.0  # Seconds of disappearance before concluding track exited
