"""
QueueSense - Visual Debugger Module
Draws bounding boxes, tracking IDs, ROI polygons, and an information HUD on frames.
"""

from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np


class DebugVisualizer:
    """
    Renders visual debug overlays on OpenCV video frames for demonstration.
    """

    def __init__(self, roi_polygon: Optional[List[Tuple[int, int]]] = None):
        if roi_polygon is None:
            roi_polygon = [(100, 100), (600, 100), (600, 600), (100, 600)]
        self.roi_polygon = np.array(roi_polygon, dtype=np.int32)

    def draw(self, frame: np.ndarray, analysis_result: Dict[str, Any]) -> np.ndarray:
        """
        Draws visual annotations onto a copy of the frame.
        
        :param frame: Original video frame
        :param analysis_result: Dictionary matching the QueueSense output contract
        :return: Annotated frame
        """
        annotated = frame.copy()

        # 1. Draw ROI polygon (semi-transparent fill + solid border)
        overlay = annotated.copy()
        cv2.fillPoly(overlay, [self.roi_polygon], color=(0, 255, 200))  # light amber/teal tint
        alpha = 0.15
        cv2.addWeighted(overlay, alpha, annotated, 1 - alpha, 0, annotated)
        cv2.polylines(annotated, [self.roi_polygon], isClosed=True, color=(0, 220, 180), thickness=2)

        # Label the ROI
        if len(self.roi_polygon) > 0:
            roi_label_pos = (self.roi_polygon[0][0] + 5, self.roi_polygon[0][1] + 20)
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

        # 2. Draw People bounding boxes and tracking IDs
        for person in analysis_result.get("people", []):
            x1, y1, x2, y2 = person["bbox"]
            pid = person.get("id", -1)
            conf = person.get("confidence", 0.0)
            in_queue = person.get("in_queue", False)

            # Color coding: Green for in queue, Cyan for outside queue
            color = (0, 255, 0) if in_queue else (255, 180, 0)
            status_text = "IN QUEUE" if in_queue else "OUTSIDE"

            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw foot position dot
            foot_x = int((x1 + x2) / 2)
            foot_y = int(y2)
            cv2.circle(annotated, (foot_x, foot_y), 4, (0, 0, 255), -1)

            # Draw tag background & text
            label = f"ID:{pid} {status_text} ({conf:.2f})"
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

        # 3. Draw HUD (Head-Up Display) summary panel
        queue_count = analysis_result.get("queue_count", 0)
        service_rate = analysis_result.get("service_rate", 0.0)
        total_served = analysis_result.get("total_served", 0)

        hud_w, hud_h = 320, 110
        cv2.rectangle(annotated, (15, 15), (15 + hud_w, 15 + hud_h), (20, 20, 20), -1)
        cv2.rectangle(annotated, (15, 15), (15 + hud_w, 15 + hud_h), (80, 80, 80), 1)

        cv2.putText(
            annotated,
            "QueueSense CV Monitor",
            (25, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            annotated,
            f"Queue Count   : {queue_count} people",
            (25, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0) if queue_count > 0 else (200, 200, 200),
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            annotated,
            f"Service Rate  : {service_rate:.2f} people/min",
            (25, 88),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 200, 255),
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            annotated,
            f"Total Served  : {total_served}",
            (25, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
            cv2.LINE_AA
        )

        return annotated
