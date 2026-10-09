"""
QueueSense - Queue Analyzer Module
Handles Region of Interest (ROI) point-in-polygon checking,
queue occupancy counting, dwell tracking, and service rate estimation.
"""

from typing import List, Tuple, Dict, Any, Optional, Union
import cv2
import numpy as np


def validate_polygon(poly: Any, name: str = "ROI polygon") -> np.ndarray:
    """
    Validates that a polygon definition has at least 3 vertices with valid 2D coordinates.
    Returns a numpy array of shape (N, 2) with dtype int32.
    """
    if poly is None:
        raise ValueError(f"{name} cannot be None.")
    if not isinstance(poly, (list, tuple, np.ndarray)) or len(poly) < 3:
        raise ValueError(f"{name} must contain at least 3 coordinate points, got {poly}.")

    pts = []
    for i, pt in enumerate(poly):
        if not (isinstance(pt, (list, tuple, np.ndarray)) and len(pt) == 2):
            raise ValueError(f"Point {i} in {name} must be a 2D (x, y) coordinate, got {pt}.")
        try:
            x, y = int(pt[0]), int(pt[1])
            pts.append((x, y))
        except (ValueError, TypeError) as err:
            raise ValueError(f"Point {i} in {name} contains non-numeric values: {pt}") from err

    return np.array(pts, dtype=np.int32)


class QueueAnalyzer:
    """
    Analyzes tracked people relative to a predefined queue Region of Interest (ROI).
    Maintains queue count and calculates the service rate based on verified service events.
    """

    def __init__(
        self,
        roi_polygon: Optional[List[Tuple[int, int]]] = None,
        service_zone: Optional[List[Tuple[int, int]]] = None,
        min_dwell_frames: int = 5,
        fps: float = 30.0,
        lost_track_expiry_frames: int = 90,
        min_observation_seconds: float = 5.0,
        manual_service_rate: Optional[float] = None
    ):
        """
        Initializes the QueueAnalyzer.
        :param roi_polygon: List of (x, y) tuples defining the queue polygon vertices (at least 3).
        :param service_zone: Optional list of (x, y) tuples defining the service counter region.
        :param min_dwell_frames: Min frames a person must dwell in queue before eligible for service.
        :param fps: Video FPS (used for elapsed time calculation if timestamps are frame-based).
        :param lost_track_expiry_frames: Frames of inactivity before pruning track from history.
        :param min_observation_seconds: Seconds of observation required before publishing automated service rate.
        :param manual_service_rate: Configurable fallback service rate in people/min when automated rate is unavailable.
        """
        if roi_polygon is None:
            # Default fallback ROI
            roi_polygon = [(100, 100), (600, 100), (600, 600), (100, 600)]

        self.roi_polygon = validate_polygon(roi_polygon, "roi_polygon")
        
        self.service_zone: Optional[np.ndarray] = None
        if service_zone is not None:
            self.service_zone = validate_polygon(service_zone, "service_zone")

        self.min_dwell_frames = max(1, int(min_dwell_frames))
        self.fps = max(fps, 1.0)
        self.lost_track_expiry_frames = max(10, int(lost_track_expiry_frames))
        self.min_observation_seconds = max(0.0, float(min_observation_seconds))
        self.manual_service_rate: Optional[float] = (
            float(manual_service_rate) if manual_service_rate is not None else None
        )

        # State tracking:
        # {person_id: {
        #     "frames_in_queue": int,
        #     "currently_in_queue": bool,
        #     "currently_in_service": bool,
        #     "last_seen_frame": int,
        #     "entered_queue_frame": Optional[int]
        # }}
        self.track_history: Dict[int, Dict[str, Any]] = {}

        # Set of person IDs that have been counted as served (prevent double counting)
        self.served_ids = set()

        # Total people who completed service
        self.total_served_count: int = 0

        # Frame and time tracking
        self.frame_index: int = 0
        self.start_time_seconds: Optional[float] = None
        self.current_time_seconds: float = 0.0

    def is_point_in_roi(self, point: Tuple[int, int]) -> bool:
        """
        Determines whether a 2D coordinate point lies inside or on the edge of the ROI polygon.
        Uses OpenCV's cv2.pointPolygonTest (>= 0 means inside or on boundary).
        """
        dist = cv2.pointPolygonTest(self.roi_polygon, (float(point[0]), float(point[1])), measureDist=False)
        return dist >= 0

    def is_point_in_service_zone(self, point: Tuple[int, int]) -> bool:
        """
        Determines whether a 2D coordinate point lies inside or on the edge of the service counter zone.
        """
        if self.service_zone is None:
            return False
        dist = cv2.pointPolygonTest(self.service_zone, (float(point[0]), float(point[1])), measureDist=False)
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
                     "service_rate": Optional[float],
                     "total_served": int
                 }
        """
        self.frame_index += 1

        # Track elapsed time
        if timestamp_seconds is not None:
            self.current_time_seconds = float(timestamp_seconds)
        else:
            self.current_time_seconds = self.frame_index / self.fps

        if self.start_time_seconds is None:
            self.start_time_seconds = self.current_time_seconds

        current_visible_ids = set()
        queue_count = 0
        enriched_people = []

        # 1. Evaluate current frame detections
        for person in people:
            pid = int(person.get("id", -1))
            raw_bbox = person.get("bbox", [0, 0, 0, 0])
            bbox = [int(coord) for coord in raw_bbox]
            conf = float(person.get("confidence", 0.0))

            # Determine position
            foot_point = self.get_bottom_center(bbox)
            in_queue = self.is_point_in_roi(foot_point)
            in_service = self.is_point_in_service_zone(foot_point)

            if in_queue:
                queue_count += 1

            enriched_people.append({
                "id": pid,
                "bbox": bbox,
                "confidence": round(conf, 3),
                "in_queue": in_queue
            })

            # For service event tracking, require a valid track ID (pid >= 0)
            if pid >= 0:
                current_visible_ids.add(pid)
                if pid not in self.track_history:
                    self.track_history[pid] = {
                        "frames_in_queue": 0,
                        "currently_in_queue": False,
                        "currently_in_service": False,
                        "last_seen_frame": self.frame_index,
                        "entered_queue_frame": self.frame_index if in_queue else None
                    }

                history = self.track_history[pid]
                history["last_seen_frame"] = self.frame_index

                # Track dwell frames
                if in_queue:
                    history["frames_in_queue"] += 1
                    history["currently_in_queue"] = True
                    if history["entered_queue_frame"] is None:
                        history["entered_queue_frame"] = self.frame_index
                else:
                    history["currently_in_queue"] = False

                # Check for explicit service event:
                # Valid service event requires:
                # 1. Person dwelled in queue for at least min_dwell_frames
                # 2. Person entered the designated service counter zone
                # 3. Person has not already been counted as served
                if self.service_zone is not None:
                    if in_service and history["frames_in_queue"] >= self.min_dwell_frames:
                        if pid not in self.served_ids:
                            self.total_served_count += 1
                            self.served_ids.add(pid)
                            history["currently_in_service"] = True
                else:
                    # When no explicit service zone is configured:
                    # We do NOT treat disappearance or simply walking out as service!
                    # Random exits, occlusions, or passersby walking through the ROI must not be counted as served.
                    pass

        # 2. Prune old inactive tracks to prevent unbounded memory growth
        # Stale tracks exceeding lost_track_expiry_frames are purged.
        # CRITICAL: Missing or occluded tracks are NEVER counted as served!
        stale_ids = [
            pid for pid, history in self.track_history.items()
            if (self.frame_index - history["last_seen_frame"]) > self.lost_track_expiry_frames
        ]
        for pid in stale_ids:
            del self.track_history[pid]

        # 3. Calculate service rate in people per minute
        elapsed_seconds = max(self.current_time_seconds - self.start_time_seconds, 0.0)
        elapsed_minutes = elapsed_seconds / 60.0

        service_rate: Optional[float] = None

        if self.total_served_count > 0 and elapsed_seconds >= self.min_observation_seconds and elapsed_minutes > 0:
            # Automated service rate backed by verified service events and sufficient observation time
            service_rate = round(float(self.total_served_count / elapsed_minutes), 2)
        elif self.manual_service_rate is not None:
            # Fallback manual service rate when automated evidence is not yet available
            service_rate = round(float(self.manual_service_rate), 2)
        else:
            # Insufficient evidence or no service zone available -> safe None
            service_rate = None

        return {
            "people": enriched_people,
            "queue_count": int(queue_count),
            "service_rate": service_rate,
            "total_served": int(self.total_served_count)
        }

    def reset(self):
        """Resets the analyzer state for a new video stream or independent session."""
        self.track_history.clear()
        self.served_ids.clear()
        self.total_served_count = 0
        self.frame_index = 0
        self.start_time_seconds = None
        self.current_time_seconds = 0.0
