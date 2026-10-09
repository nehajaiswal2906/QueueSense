"""
QueueSense - Person Detector & Tracker Module
Utilizes pretrained YOLOv8 with ByteTrack for person detection and tracking.
"""

from typing import List, Dict, Any, Optional
import os
import torch
import numpy as np
from ultralytics import YOLO


class PersonTracker:
    """
    Detects and tracks people across video frames using a pretrained YOLO model.
    Filters specifically for COCO class 0 (person).
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_thresh: float = 0.35,
        tracker_type: str = "bytetrack.yaml",
        device: Optional[str] = None
    ):
        """
        Initializes the YOLO model and tracking parameters.
        :param model_path: Path to YOLO weights (pretrained YOLOv8n used for speed on CPU)
        :param conf_thresh: Minimum confidence score to accept a detection
        :param tracker_type: Tracker configuration file ('bytetrack.yaml' or 'botsort.yaml')
        :param device: Inference device ('cpu', 'cuda', 'cuda:0', or None for auto-detect)
        """
        if not os.path.exists(model_path) and not model_path.endswith(".pt"):
            raise FileNotFoundError(f"Model weight file not found at: {model_path}")

        self.model = YOLO(model_path)
        self.conf_thresh = max(0.0, min(1.0, float(conf_thresh)))
        self.tracker_type = tracker_type
        
        # Safe device selection: use CUDA only if available and requested/auto
        if device is not None:
            self.device = device
        else:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

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
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0 or len(frame.shape) < 2:
            return []

        frame_h, frame_w = frame.shape[:2]

        try:
            # Run YOLO with tracking enabled, filtering strictly for class 0 (person)
            results = self.model.track(
                source=frame,
                persist=persist,
                classes=[0],  # 0 is 'person' in COCO
                conf=self.conf_thresh,
                tracker=self.tracker_type,
                device=self.device,
                verbose=False
            )
        except Exception as e:
            # Handle unexpected frame or tracker exceptions gracefully
            print(f"[QueueSense Detector Warning] Tracking failed on frame: {e}")
            return []

        tracked_people: List[Dict[str, Any]] = []

        if not results or len(results) == 0:
            return tracked_people

        result = results[0]
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            return tracked_people

        for box in boxes:
            # Extract bounding box coordinates [x1, y1, x2, y2]
            xyxy = box.xyxy[0].cpu().numpy()
            x1 = max(0, min(frame_w, int(round(xyxy[0]))))
            y1 = max(0, min(frame_h, int(round(xyxy[1]))))
            x2 = max(x1, min(frame_w, int(round(xyxy[2]))))
            y2 = max(y1, min(frame_h, int(round(xyxy[3]))))

            conf = float(box.conf[0].cpu().numpy())
            conf = max(0.0, min(1.0, conf))

            # Track ID if available, otherwise fallback to -1
            if box.id is not None:
                track_id = int(box.id[0].cpu().numpy())
            else:
                track_id = -1

            tracked_people.append({
                "id": track_id,
                "bbox": [x1, y1, x2, y2],
                "confidence": round(conf, 3)
            })

        return tracked_people

    def reset(self):
        """
        Resets ByteTrack tracker state so independent sessions do not carry over previous track IDs.
        """
        if hasattr(self.model, "predictor") and self.model.predictor is not None:
            trackers = getattr(self.model.predictor, "trackers", None)
            if trackers:
                for tracker in trackers:
                    if hasattr(tracker, "reset"):
                        tracker.reset()

