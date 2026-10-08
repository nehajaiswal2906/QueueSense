"""
QueueSense - Queue Analyzer Module
Handles Region of Interest (ROI) point-in-polygon checking,
queue occupancy counting, and service rate estimation.
"""

from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np


class QueueAnalyzer:
    """
    Analyzes tracked people relative to a predefined queue Region of Interest (ROI).
    Maintains queue count and calculates the service rate based on departures.
    """

    def __init__(
        self,
        roi_polygon: Optional[List[Tuple[int, int]]] = None,
        min_dwell_frames: int = 5,
        fps: float = 30.0
    ):
        """
        Initializes the QueueAnalyzer.
        :param roi_polygon: List of (x, y) tuples defining the queue polygon vertices.
        :param min_dwell_frames: Min frames a person must be in queue before departure counts as served.
        :param fps: Video FPS (used for elapsed time calculation if timestamps are frame-based).
        """
        if roi_polygon is None:
            # Default fallback ROI
            roi_polygon = [(100, 100), (600, 100), (600, 600), (100, 600)]

        self.roi_polygon = np.array(roi_polygon, dtype=np.int32)
        self.min_dwell_frames = min_dwell_frames
        self.fps = max(fps, 1.0)

        # State tracking:
        # {person_id: {"frames_in_queue": int, "last_in_queue": bool, "last_seen_frame": int}}
        self.track_history: Dict[int, Dict[str, Any]] = {}

        # Set of person IDs that have been counted as served (to prevent double counting)
        self.served_ids = set()

        # Total people who have left the queue after being served
        self.total_served_count: int = 0

        # Frame and time tracking
        self.frame_index: int = 0
        self.start_time_seconds: Optional[float] = None
        self.current_time_seconds: float = 0.0

    def is_point_in_roi(self, point: Tuple[int, int]) -> bool:
        """
        Determines whether a 2D coordinate point lies inside or on the edge of the ROI polygon.
        Uses OpenCV's cv2.pointPolygonTest (positive or 0 means inside/on edge).
        """
        # cv2.pointPolygonTest returns >0 if inside, 0 if on edge, <0 if outside
        dist = cv2.pointPolygonTest(self.roi_polygon, (float(point[0]), float(point[1])), measureDist=False)
        return dist >= 0

    @staticmethod
    def get_bottom_center(bbox: List[int]) -> Tuple[int, int]:
        """
        Computes the bottom-center point of a bounding box [x1, y1, x2, y2].
        The bottom center represents the person's feet on the ground,
        providing the most accurate queue position.
        """
        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2)
        bottom_y = int(y2)
        return center_x, bottom_y

    def update(
        self,
        people: List[Dict[str, Any]],
        timestamp_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Processes tracked people in the current frame.
        Determines who is inside the queue, updates queue counts, and calculates service rate.

        :param people: List of dicts [{"id": int, "bbox": [x1, y1, x2, y2], "confidence": float}]
        :param timestamp_seconds: Optional explicit timestamp in seconds.
        :return: Standardized result contract:
                 {
                     "people": [
                         {"id": int, "bbox": [...], "confidence": float, "in_queue": bool}
                     ],
                     "queue_count": int,
                     "service_rate": float
                 }
        """
        self.frame_index += 1

        # Track elapsed time
        if timestamp_seconds is not None:
            self.current_time_seconds = timestamp_seconds
        else:
            self.current_time_seconds = self.frame_index / self.fps

        if self.start_time_seconds is None:
            self.start_time_seconds = self.current_time_seconds

        current_visible_ids = set()
        queue_count = 0
        enriched_people = []

        # 1. Evaluate current frame detections
        for person in people:
            pid = person.get("id", -1)
            bbox = person.get("bbox", [0, 0, 0, 0])
            conf = person.get("confidence", 0.0)

            # Determine if person is inside queue ROI
            foot_point = self.get_bottom_center(bbox)
            in_queue = self.is_point_in_roi(foot_point)

            if in_queue:
                queue_count += 1

            enriched_people.append({
                "id": pid,
                "bbox": bbox,
                "confidence": conf,
                "in_queue": in_queue
            })

            if pid >= 0:
                current_visible_ids.add(pid)
                if pid not in self.track_history:
                    self.track_history[pid] = {
                        "frames_in_queue": 0,
                        "currently_in_queue": False,
                        "last_seen_frame": self.frame_index
                    }

                history = self.track_history[pid]
                history["last_seen_frame"] = self.frame_index

                # Check if person was previously in queue and just stepped out
                if history["currently_in_queue"] and not in_queue:
                    # They transitioned from inside the queue to outside
                    if history["frames_in_queue"] >= self.min_dwell_frames and pid not in self.served_ids:
                        self.total_served_count += 1
                        self.served_ids.add(pid)

                if in_queue:
                    history["frames_in_queue"] += 1
                    history["currently_in_queue"] = True
                else:
                    history["currently_in_queue"] = False

        # 2. Check for tracks that disappeared while in the queue (e.g. left camera view after service)
        # Only evaluate tracks not seen for at least 3 consecutive frames
        for pid, history in list(self.track_history.items()):
            if pid not in current_visible_ids:
                frames_inactive = self.frame_index - history["last_seen_frame"]
                if frames_inactive >= 3:
                    if (
                        history["currently_in_queue"]
                        and history["frames_in_queue"] >= self.min_dwell_frames
                        and pid not in self.served_ids
                    ):
                        self.total_served_count += 1
                        self.served_ids.add(pid)
                        history["currently_in_queue"] = False

        # 3. Calculate service rate (people leaving queue / observation time in minutes)
        elapsed_seconds = max(self.current_time_seconds - self.start_time_seconds, 0.0)
        elapsed_minutes = elapsed_seconds / 60.0

        if elapsed_minutes > 0.05:  # Start reporting service rate after ~3 seconds of observation
            service_rate = round(self.total_served_count / elapsed_minutes, 2)
        else:
            # Not enough elapsed observation time yet
            service_rate = 0.0

        return {
            "people": enriched_people,
            "queue_count": queue_count,
            "service_rate": service_rate,
            "total_served": self.total_served_count
        }

    def reset(self):
        """Resets the analyzer state for a new video stream."""
        self.track_history.clear()
        self.served_ids.clear()
        self.total_served_count = 0
        self.frame_index = 0
        self.start_time_seconds = None
        self.current_time_seconds = 0.0
