"""
QueueSense - Person Detector & Tracker Module
Utilizes pretrained YOLOv8 with ByteTrack for person detection and tracking.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from ultralytics import YOLO


class PersonTracker:
    """
    Detects and tracks people across video frames using a pretrained YOLO model.
    Filters specifically for COCO class 0 (person).
    """

    def __init__(self, model_path: str = "yolov8n.pt", conf_thresh: float = 0.35, tracker_type: str = "bytetrack.yaml"):
        """
        Initializes the YOLO model and tracking parameters.
        :param model_path: Path to YOLO weights (pretrained YOLOv8n used for speed on CPU)
        :param conf_thresh: Minimum confidence score to accept a detection
        :param tracker_type: Tracker configuration file ('bytetrack.yaml' or 'botsort.yaml')
        """
        self.model = YOLO(model_path)
        self.conf_thresh = conf_thresh
        self.tracker_type = tracker_type

    def detect_and_track(self, frame: np.ndarray, persist: bool = True) -> List[Dict[str, Any]]:
        """
        Runs person detection and tracking on a single image/video frame.
        
        :param frame: BGR image frame from OpenCV
        :param persist: Whether to persist track history across frames
        :return: List of detected/tracked people:
                 [
                     {"id": int, "bbox": [x1, y1, x2, y2], "confidence": float}
                 ]
        """
        if frame is None or frame.size == 0:
            return []

        # Run YOLO with tracking enabled, filtering strictly for class 0 (person)
        results = self.model.track(
            source=frame,
            persist=persist,
            classes=[0],  # 0 is 'person' in COCO
            conf=self.conf_thresh,
            tracker=self.tracker_type,
            verbose=False
        )

        tracked_people = []

        if not results or len(results) == 0:
            return tracked_people

        result = results[0]
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            return tracked_people

        for box in boxes:
            # Extract bounding box coordinates [x1, y1, x2, y2]
            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = [int(round(coord)) for coord in xyxy]

            conf = float(box.conf[0].cpu().numpy())

            # Track ID if available, otherwise fallback to -1
            track_id = int(box.id[0].cpu().numpy()) if box.id is not None else -1

            tracked_people.append({
                "id": track_id,
                "bbox": [x1, y1, x2, y2],
                "confidence": round(conf, 3)
            })

        return tracked_people
