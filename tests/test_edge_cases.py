"""
QueueSense - Edge Case Verification Suite
Tests the 8 critical edge cases:
1. No people
2. One person
3. Multiple people
4. People entering queue
5. People leaving queue
6. People overlapping / occluding each other
7. Person outside ROI
8. Low-quality or slightly shaky video
"""

import sys
import os
import unittest
import numpy as np
import cv2

# Ensure parent directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from queue_analyzer import QueueAnalyzer
from pipeline import QueueSensePipeline


class TestQueueSenseEdgeCases(unittest.TestCase):

    def setUp(self):
        # Standard ROI for tests: a square from (100, 100) to (300, 300)
        self.roi = [(100, 100), (300, 100), (300, 300), (100, 300)]
        self.analyzer = QueueAnalyzer(roi_polygon=self.roi, min_dwell_frames=3, fps=30.0)

    def test_edge_case_1_no_people(self):
        """Edge Case 1: Empty scene (no people detected)."""
        result = self.analyzer.update([])
        self.assertEqual(result["queue_count"], 0)
        self.assertEqual(len(result["people"]), 0)
        self.assertEqual(result["service_rate"], 0.0)
        self.assertEqual(result["total_served"], 0)

    def test_edge_case_2_one_person_inside_and_outside(self):
        """Edge Case 2: One person, tested inside vs outside."""
        # Person inside ROI: foot at (200, 250) -> inside [100..300, 100..300]
        person_inside = [{"id": 1, "bbox": [150, 150, 250, 250], "confidence": 0.92}]
        res_in = self.analyzer.update(person_inside)
        self.assertEqual(res_in["queue_count"], 1)
        self.assertTrue(res_in["people"][0]["in_queue"])

        # Reset analyzer
        self.analyzer.reset()

        # Person outside ROI: foot at (50, 50)
        person_outside = [{"id": 2, "bbox": [20, 20, 80, 50], "confidence": 0.88}]
        res_out = self.analyzer.update(person_outside)
        self.assertEqual(res_out["queue_count"], 0)
        self.assertFalse(res_out["people"][0]["in_queue"])

    def test_edge_case_3_multiple_people(self):
        """Edge Case 3: Multiple people present simultaneously."""
        # 2 people inside ROI, 1 person outside ROI
        people = [
            {"id": 1, "bbox": [120, 120, 180, 220], "confidence": 0.91},  # foot: (150, 220) -> INSIDE
            {"id": 2, "bbox": [220, 150, 280, 250], "confidence": 0.89},  # foot: (250, 250) -> INSIDE
            {"id": 3, "bbox": [400, 100, 450, 200], "confidence": 0.85},  # foot: (425, 200) -> OUTSIDE
        ]
        result = self.analyzer.update(people)
        self.assertEqual(result["queue_count"], 2)
        self.assertEqual(len(result["people"]), 3)
        self.assertTrue(result["people"][0]["in_queue"])
        self.assertTrue(result["people"][1]["in_queue"])
        self.assertFalse(result["people"][2]["in_queue"])

    def test_edge_case_4_people_entering_queue(self):
        """Edge Case 4: Person transitions from outside to inside queue ROI."""
        # Frame 1: Person outside ROI
        p_frame1 = [{"id": 10, "bbox": [30, 150, 80, 250], "confidence": 0.90}]  # foot: (55, 250) OUTSIDE
        res1 = self.analyzer.update(p_frame1)
        self.assertEqual(res1["queue_count"], 0)
        self.assertFalse(res1["people"][0]["in_queue"])

        # Frame 2: Person enters ROI
        p_frame2 = [{"id": 10, "bbox": [150, 150, 200, 250], "confidence": 0.92}]  # foot: (175, 250) INSIDE
        res2 = self.analyzer.update(p_frame2)
        self.assertEqual(res2["queue_count"], 1)
        self.assertTrue(res2["people"][0]["in_queue"])

    def test_edge_case_5_people_leaving_queue_and_service_rate(self):
        """Edge Case 5: Person dwells in queue, then leaves. Verifies departure and service rate."""
        # Person 5 dwells inside queue for 4 frames (min_dwell is 3)
        p_in = [{"id": 5, "bbox": [150, 150, 250, 250], "confidence": 0.95}]
        for i in range(4):
            res = self.analyzer.update(p_in, timestamp_seconds=i * 1.0)
            self.assertEqual(res["queue_count"], 1)

        # Person 5 steps OUTSIDE the ROI at t = 5.0 seconds
        p_out = [{"id": 5, "bbox": [350, 150, 450, 250], "confidence": 0.95}]
        res_after = self.analyzer.update(p_out, timestamp_seconds=5.0)

        # Queue count should drop to 0, served should be 1
        self.assertEqual(res_after["queue_count"], 0)
        self.assertEqual(res_after["total_served"], 1)

        # Simulate 1 minute of elapsed time (60 seconds) with 1 person served
        res_time = self.analyzer.update([], timestamp_seconds=60.0)
        # service_rate = 1 person / (60/60 min) = 1.0 person/min
        self.assertEqual(res_time["total_served"], 1)
        self.assertEqual(res_time["service_rate"], 1.0)

    def test_edge_case_6_overlapping_people(self):
        """Edge Case 6: People overlapping / occluding each other."""
        # Two bounding boxes that overlap heavily in (x, y) space
        p1 = {"id": 101, "bbox": [140, 120, 200, 260], "confidence": 0.90}  # foot: (170, 260) INSIDE
        p2 = {"id": 102, "bbox": [150, 130, 210, 270], "confidence": 0.88}  # foot: (180, 270) INSIDE

        res = self.analyzer.update([p1, p2])
        self.assertEqual(res["queue_count"], 2)
        self.assertTrue(res["people"][0]["in_queue"])
        self.assertTrue(res["people"][1]["in_queue"])

    def test_edge_case_7_person_outside_roi(self):
        """Edge Case 7: Person clearly outside ROI is never counted."""
        outside_people = [
            {"id": 201, "bbox": [10, 10, 50, 80], "confidence": 0.94},    # foot: (30, 80)
            {"id": 202, "bbox": [500, 500, 550, 580], "confidence": 0.89} # foot: (525, 580)
        ]
        res = self.analyzer.update(outside_people)
        self.assertEqual(res["queue_count"], 0)
        self.assertFalse(res["people"][0]["in_queue"])
        self.assertFalse(res["people"][1]["in_queue"])

    def test_edge_case_8_low_quality_and_shaky_frame(self):
        """Edge Case 8: Frame degradation (noise, shake, blur)."""
        # Create a mock synthetic frame with noise
        frame = np.full((400, 400, 3), 128, dtype=np.uint8)
        noise = np.random.normal(0, 25, frame.shape).astype(np.int16)
        shaky_frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Pipeline must handle noisy frame gracefully without error
        pipeline = QueueSensePipeline(roi_polygon=self.roi)
        result = pipeline.process_frame(shaky_frame)

        self.assertIn("people", result)
        self.assertIn("queue_count", result)
        self.assertIn("service_rate", result)
        self.assertIsInstance(result["queue_count"], int)
        self.assertIsInstance(result["service_rate"], float)


if __name__ == "__main__":
    unittest.main()
