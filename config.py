"""
QueueSense Configuration
Defines default parameters, ROI coordinates, model choice, and thresholds.
"""

from typing import List, Tuple, Optional

# Default video path for demo and evaluation
DEFAULT_VIDEO_PATH: str = "assets/canteen_queue_demo.mp4"
BASE_RESOLUTION: Tuple[int, int] = (1280, 720)

# Calibrated Region of Interest for canteen_queue_demo.mp4 (1280x720)
# Covers the central counter queue waiting line where customers wait with carts/baskets
DEFAULT_QUEUE_ROI: List[Tuple[int, int]] = [
    (280, 200),
    (750, 200),
    (750, 690),
    (280, 690)
]

# Calibrated Service / Counter Zone (Polygon vertices in (x, y) coordinates)
# Counter payment and checkout collection station where customers step up to complete service
# Customers who dwell in the queue ROI and transition into this zone are verified as served
DEFAULT_SERVICE_ZONE: Optional[List[Tuple[int, int]]] = [
    (180, 450),
    (280, 450),
    (280, 710),
    (180, 710)
]

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


def scale_polygon(
    polygon: List[Tuple[int, int]],
    src_size: Tuple[int, int],
    dst_size: Tuple[int, int]
) -> List[Tuple[int, int]]:
    """
    Scales polygon vertex coordinates from src_size (w, h) to dst_size (w, h).
    Guarantees ROI coordinates remain accurate if video resolution changes.
    """
    src_w, src_h = src_size
    dst_w, dst_h = dst_size
    if src_w <= 0 or src_h <= 0 or (src_w == dst_w and src_h == dst_h):
        return polygon

    scale_x = float(dst_w) / float(src_w)
    scale_y = float(dst_h) / float(src_h)

    return [(int(round(x * scale_x)), int(round(y * scale_y))) for (x, y) in polygon]

