"""
QueueSense Pipeline
Main Computer Vision pipeline integrating YOLO detection, ByteTrack tracking,
Queue ROI point-in-polygon logic, and Service Rate estimation.
Exposes a clean API for Team B / Flask backend integration.
"""

from typing import List, Tuple, Dict, Any, Optional, Iterator
import cv2
import numpy as np

from detector import PersonTracker
from queue_analyzer import QueueAnalyzer
from debug_visualizer import DebugVisualizer
import config


class QueueSensePipeline:
    """
    Unified Computer Vision pipeline for QueueSense.
    
    Usage for Team B (Flask Backend):
        pipeline = QueueSensePipeline(roi_polygon=[(100, 100), (600, 100), (600, 600), (100, 600)])
        result = pipeline.process_frame(frame)
        print(result["queue_count"], result["service_rate"])
    """

    def __init__(
        self,
        roi_polygon: Optional[List[Tuple[int, int]]] = None,
        model_path: str = config.MODEL_PATH,
        conf_thresh: float = config.CONFIDENCE_THRESHOLD,
        fps: float = 30.0,
        min_dwell_frames: int = config.MIN_QUEUE_DWELL_FRAMES
    ):
        """
        Initializes detector, tracker, and queue analyzer.
        """
        self.roi_polygon = roi_polygon if roi_polygon is not None else config.DEFAULT_QUEUE_ROI
        self.tracker = PersonTracker(model_path=model_path, conf_thresh=conf_thresh)
        self.analyzer = QueueAnalyzer(roi_polygon=self.roi_polygon, min_dwell_frames=min_dwell_frames, fps=fps)
        self.visualizer = DebugVisualizer(roi_polygon=self.roi_polygon)

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Processes a single frame and returns clean QueueSense output matching the integration contract.

        :param frame: OpenCV BGR image array
        :param timestamp_seconds: Optional elapsed time timestamp in seconds
        :return: {
            "people": [
                {
                    "id": int,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": float,
                    "in_queue": bool
                }
            ],
            "queue_count": int,
            "service_rate": float
        }
        """
        if frame is None or frame.size == 0:
            return {
                "people": [],
                "queue_count": 0,
                "service_rate": 0.0
            }

        # 1. Detect and track people
        tracked_people = self.tracker.detect_and_track(frame, persist=True)

        # 2. Analyze queue occupancy and service rate
        analysis = self.analyzer.update(tracked_people, timestamp_seconds=timestamp_seconds)

        # 3. Format strictly according to output contract
        return {
            "people": analysis["people"],
            "queue_count": analysis["queue_count"],
            "service_rate": analysis["service_rate"]
        }

    def render_debug_frame(self, frame: np.ndarray, result: Dict[str, Any]) -> np.ndarray:
        """
        Draws visual debugging overlays (boxes, IDs, ROI, HUD stats) onto the frame.
        """
        return self.visualizer.draw(frame, result)

    def stream_video(
        self,
        video_source: Any,
        debug: bool = False
    ) -> Iterator[Tuple[Dict[str, Any], Optional[np.ndarray]]]:
        """
        Generator yielding (contract_result, annotated_or_raw_frame) frame by frame.
        Useful for streaming video processing or websocket feeds.
        """
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video source: {video_source}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.analyzer.fps = fps

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                result = self.process_frame(frame)
                annotated = self.render_debug_frame(frame, result) if debug else None
                yield result, annotated
        finally:
            cap.release()

    def reset(self):
        """Resets tracker and queue state."""
        self.analyzer.reset()


def create_pipeline(
    roi_polygon: Optional[List[Tuple[int, int]]] = None,
    conf_thresh: float = config.CONFIDENCE_THRESHOLD,
    fps: float = 30.0
) -> QueueSensePipeline:
    """
    Factory function for Team B to easily obtain a configured pipeline.
    """
    return QueueSensePipeline(roi_polygon=roi_polygon, conf_thresh=conf_thresh, fps=fps)
