"""
QueueSense - Visual Debugger Module
Draws bounding boxes, tracking IDs, ROI polygons, and an informative HUD on video frames.
Supports headless execution, graceful None handling, and service counter zone display.
"""

from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np


class DebugVisualizer:
    """
    Renders visual debug overlays on OpenCV video frames for demonstration.
    """

    def __init__(
        self,
        roi_polygon: Optional[List[Tuple[int, int]]] = None,
        service_zone: Optional[List[Tuple[int, int]]] = None
    ):
        if roi_polygon is None:
            roi_polygon = [(100, 100), (600, 100), (600, 600), (100, 600)]
        self.roi_polygon = np.array(roi_polygon, dtype=np.int32)
        
        self.service_zone: Optional[np.ndarray] = None
        if service_zone is not None:
            self.service_zone = np.array(service_zone, dtype=np.int32)

    def draw(self, frame: np.ndarray, analysis_result: Dict[str, Any]) -> np.ndarray:
        """
        Draws visual annotations onto a copy of the frame.
        
        :param frame: Original video frame
        :param analysis_result: Dictionary matching the QueueSense output contract
        :return: Annotated frame
        """
        if frame is None or frame.size == 0:
            return frame

        annotated = frame.copy()

        # 1. Draw Queue ROI polygon (semi-transparent fill + solid border)
        if len(self.roi_polygon) >= 3:
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [self.roi_polygon], color=(0, 255, 200))  # light amber/teal tint
            alpha = 0.15
            cv2.addWeighted(overlay, alpha, annotated, 1 - alpha, 0, annotated)
            cv2.polylines(annotated, [self.roi_polygon], isClosed=True, color=(0, 220, 180), thickness=2)

            roi_label_pos = (int(self.roi_polygon[0][0]) + 5, int(self.roi_polygon[0][1]) + 20)
            cv2.putText(
                annotated,
                "QUEUE ROI",
                roi_label_pos,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 220, 180),
                2,
                cv2.LINE_AA
            )

        # 2. Draw Service Counter Zone if configured
        if self.service_zone is not None and len(self.service_zone) >= 3:
            svc_overlay = annotated.copy()
            cv2.fillPoly(svc_overlay, [self.service_zone], color=(255, 140, 0))  # orange tint
            cv2.addWeighted(svc_overlay, 0.15, annotated, 0.85, 0, annotated)
            cv2.polylines(annotated, [self.service_zone], isClosed=True, color=(255, 140, 0), thickness=2)

            svc_label_pos = (int(self.service_zone[0][0]) + 5, int(self.service_zone[0][1]) + 20)
            cv2.putText(
                annotated,
                "SERVICE COUNTER",
                svc_label_pos,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 160, 20),
                2,
                cv2.LINE_AA
            )

        # 3. Draw People bounding boxes and tracking IDs
        for person in analysis_result.get("people", []):
            bbox = person.get("bbox", [0, 0, 0, 0])
            x1, y1, x2, y2 = [int(c) for c in bbox]
            pid = person.get("id", -1)
            conf = float(person.get("confidence", 0.0))
            in_queue = bool(person.get("in_queue", False))

            # Color coding: Green for in queue, Amber for outside
            color = (0, 255, 0) if in_queue else (255, 180, 0)
            status_text = "IN QUEUE" if in_queue else "OUTSIDE"

            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw foot position dot
            foot_x = int((x1 + x2) / 2)
            foot_y = int(y2)
            cv2.circle(annotated, (foot_x, foot_y), 4, (0, 0, 255), -1)

            # Draw tag background & text
            id_str = f"ID:{pid}" if pid >= 0 else "ID:?"
            label = f"{id_str} {status_text} ({conf:.2f})"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            tag_y1 = max(0, y1 - 20)
            tag_y2 = y1
            cv2.rectangle(annotated, (x1, tag_y1), (x1 + w + 6, tag_y2), color, -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 3, tag_y2 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                1,
                cv2.LINE_AA
            )

        # 4. Draw HUD (Head-Up Display) summary panel
        queue_count = int(analysis_result.get("queue_count", 0))
        service_rate_val = analysis_result.get("service_rate")
        total_served = int(analysis_result.get("total_served", 0))

        if service_rate_val is not None and isinstance(service_rate_val, (int, float)):
            service_rate_str = f"{float(service_rate_val):.2f} people/min"
            service_rate_color = (0, 200, 255)
        else:
            service_rate_str = "N/A (Awaiting data)"
            service_rate_color = (160, 160, 160)

        hud_w, hud_h = 340, 115
        cv2.rectangle(annotated, (15, 15), (15 + hud_w, 15 + hud_h), (20, 20, 20), -1)
        cv2.rectangle(annotated, (15, 15), (15 + hud_w, 15 + hud_h), (80, 80, 80), 1)

        cv2.putText(
            annotated,
            "QueueSense CV Monitor (Team A)",
            (25, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            annotated,
            f"Queue Count   : {queue_count} people",
            (25, 63),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0) if queue_count > 0 else (200, 200, 200),
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            annotated,
            f"Service Rate  : {service_rate_str}",
            (25, 86),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            service_rate_color,
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            annotated,
            f"Total Served  : {total_served}",
            (25, 108),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
            cv2.LINE_AA
        )

        return annotated
