"""
QueueSense Configuration
Defines default parameters, ROI coordinates, model choice, and thresholds.
"""

from typing import List, Tuple, Optional

# Default Region of Interest (Polygon vertices in (x, y) coordinates)
# Adjust these coordinates to match the camera angle / queue area of the venue.
DEFAULT_QUEUE_ROI: List[Tuple[int, int]] = [
    (100, 100),
    (600, 100),
    (600, 600),
    (100, 600)
]

# Optional Service / Counter Zone (Polygon vertices in (x, y) coordinates)
# People who dwelled in the queue ROI and transition into this zone are counted as served.
# If None, automated service rate is only computed when an explicit service zone is provided,
# or falls back to MANUAL_SERVICE_RATE if defined.
DEFAULT_SERVICE_ZONE: Optional[List[Tuple[int, int]]] = None

# Model settings
MODEL_PATH: str = "yolov8n.pt"  # Lightweight pretrained YOLOv8 nano
CONFIDENCE_THRESHOLD: float = 0.35  # Confidence threshold for person detection
TRACKER_TYPE: str = "bytetrack.yaml"

# Queue analysis parameters
MIN_QUEUE_DWELL_FRAMES: int = 5  # Minimum frames inside ROI before eligible for service
LOST_TRACK_EXPIRY_FRAMES: int = 90  # Inactive frames before pruning track history (~3s at 30fps)
LOST_TRACK_EXPIRY_SECONDS: float = 2.0  # Kept for backward compatibility
MIN_OBSERVATION_SECONDS: float = 5.0  # Observation time needed before publishing automated service rate
MANUAL_SERVICE_RATE: Optional[float] = None  # Fallback manual rate in people/min if automated is unavailable
