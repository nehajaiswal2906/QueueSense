"""
QueueSense - Comprehensive Unit Test Suite
Covers all 17 critical test scenarios for queue detection, tracking, service rate, and contract integrity:

 1. Empty scene gives queue_count = 0.
 2. One person inside the ROI.
 3. One person outside the ROI.
 4. Several people inside and outside the ROI.
 5. A person entering the queue.
 6. A person leaving the queue without being incorrectly assumed served.
 7. A valid service event being counted exactly once.
 8. Temporary occlusion not automatically counting as service.
 9. A missing tracking ID.
10. A person re-entering the queue.
11. Dwell-time and visit-history handling.
12. Reset between independent sessions.
13. Invalid or empty frame handling.
14. Output contract fields and types.
15. JSON serialization.
16. Zero or unavailable service rate.
17. Invalid ROI configuration.
"""

import sys
import os
import unittest
import json
import numpy as np

# Ensure parent directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from queue_analyzer import QueueAnalyzer, validate_polygon
from pipeline import QueueSensePipeline


class TestQueueSenseComprehensive(unittest.TestCase):

    def setUp(self):
        # Standard queue ROI: square from (100, 100) to (300, 300)
        self.roi = [(100, 100), (300, 100), (300, 300), (100, 300)]
        # Adjacent service counter zone from (300, 100) to (450, 300)
        self.service_zone = [(300, 100), (450, 100), (450, 300), (300, 300)]
        self.analyzer = QueueAnalyzer(
            roi_polygon=self.roi,
            service_zone=self.service_zone,
            min_dwell_frames=3,
            fps=30.0,
            min_observation_seconds=5.0
        )

    # --------------------------------------------------------------------------
    # Scenario 1: Empty scene gives queue_count = 0
    # --------------------------------------------------------------------------
    def test_01_empty_scene_gives_zero_count(self):
        result = self.analyzer.update([])
        self.assertEqual(result["queue_count"], 0)
        self.assertEqual(len(result["people"]), 0)
        self.assertIsNone(result["service_rate"])
        self.assertEqual(result["total_served"], 0)

    # --------------------------------------------------------------------------
    # Scenario 2: One person inside ROI
    # --------------------------------------------------------------------------
    def test_02_one_person_inside_roi(self):
        # Foot point at bottom center: ( (150+250)/2, 250 ) = (200, 250) -> INSIDE [100..300, 100..300]
        person = [{"id": 1, "bbox": [150, 150, 250, 250], "confidence": 0.92}]
        res = self.analyzer.update(person)
        self.assertEqual(res["queue_count"], 1)
        self.assertEqual(len(res["people"]), 1)
        self.assertTrue(res["people"][0]["in_queue"])

    # --------------------------------------------------------------------------
    # Scenario 3: One person outside ROI
    # --------------------------------------------------------------------------
    def test_03_one_person_outside_roi(self):
        # Foot point: ( (20+80)/2, 50 ) = (50, 50) -> OUTSIDE
        person = [{"id": 2, "bbox": [20, 20, 80, 50], "confidence": 0.88}]
        res = self.analyzer.update(person)
        self.assertEqual(res["queue_count"], 0)
        self.assertFalse(res["people"][0]["in_queue"])

    # --------------------------------------------------------------------------
    # Scenario 4: Several people inside and outside ROI
    # --------------------------------------------------------------------------
    def test_04_several_people_inside_and_outside_roi(self):
        people = [
            {"id": 1, "bbox": [120, 120, 180, 220], "confidence": 0.91},  # foot: (150, 220) -> INSIDE
            {"id": 2, "bbox": [220, 150, 280, 250], "confidence": 0.89},  # foot: (250, 250) -> INSIDE
            {"id": 3, "bbox": [460, 100, 500, 200], "confidence": 0.85},  # foot: (480, 200) -> OUTSIDE
        ]
        res = self.analyzer.update(people)
        self.assertEqual(res["queue_count"], 2)
        self.assertEqual(len(res["people"]), 3)
        self.assertTrue(res["people"][0]["in_queue"])
        self.assertTrue(res["people"][1]["in_queue"])
        self.assertFalse(res["people"][2]["in_queue"])

    # --------------------------------------------------------------------------
    # Scenario 5: A person entering the queue
    # --------------------------------------------------------------------------
    def test_05_person_entering_queue(self):
        # Frame 1: Person outside
        p_f1 = [{"id": 10, "bbox": [20, 150, 80, 250], "confidence": 0.90}]
        res1 = self.analyzer.update(p_f1)
        self.assertEqual(res1["queue_count"], 0)
        self.assertFalse(res1["people"][0]["in_queue"])

        # Frame 2: Person steps inside
        p_f2 = [{"id": 10, "bbox": [150, 150, 200, 250], "confidence": 0.92}]
        res2 = self.analyzer.update(p_f2)
        self.assertEqual(res2["queue_count"], 1)
        self.assertTrue(res2["people"][0]["in_queue"])

    # --------------------------------------------------------------------------
    # Scenario 6: Person leaving queue without being incorrectly assumed served
    # --------------------------------------------------------------------------
    def test_06_person_leaving_queue_not_assumed_served(self):
        # Person dwells in queue for 4 frames (min_dwell = 3)
        p_in = [{"id": 5, "bbox": [150, 150, 250, 250], "confidence": 0.95}]
        for _ in range(4):
            self.analyzer.update(p_in)

        # Person steps outside the queue to (50, 250) which is NOT the service zone
        p_out = [{"id": 5, "bbox": [20, 150, 80, 250], "confidence": 0.95}]
        res_after = self.analyzer.update(p_out)

        # Queue count drops, but total_served MUST remain 0 (leaving != served)
        self.assertEqual(res_after["queue_count"], 0)
        self.assertEqual(res_after["total_served"], 0)

    # --------------------------------------------------------------------------
    # Scenario 7: A valid service event being counted exactly once
    # --------------------------------------------------------------------------
    def test_07_valid_service_event_counted_exactly_once(self):
        # Person 7 dwells in queue for 4 frames
        p_in = [{"id": 7, "bbox": [150, 150, 250, 250], "confidence": 0.95}]
        for _ in range(4):
            self.analyzer.update(p_in)

        # Person 7 moves to service counter zone: foot at (350, 200) inside service_zone
        p_service = [{"id": 7, "bbox": [320, 120, 380, 200], "confidence": 0.95}]
        res1 = self.analyzer.update(p_service)

        self.assertEqual(res1["queue_count"], 0)
        self.assertEqual(res1["total_served"], 1)

        # Person stays in service zone for 3 more frames - must not be double counted!
        for _ in range(3):
            res_stay = self.analyzer.update(p_service)
            self.assertEqual(res_stay["total_served"], 1)

    # --------------------------------------------------------------------------
    # Scenario 8: Temporary occlusion not automatically counting as service
    # --------------------------------------------------------------------------
    def test_08_temporary_occlusion_not_counting_as_service(self):
        # Person dwells in queue
        p = [{"id": 8, "bbox": [150, 150, 250, 250], "confidence": 0.90}]
        for _ in range(4):
            self.analyzer.update(p)

        # Person temporarily occluded / missing for 5 frames
        for _ in range(5):
            res_occluded = self.analyzer.update([])
            self.assertEqual(res_occluded["total_served"], 0, "Missing track must NOT be counted as served!")

        # Person reappears
        res_reappear = self.analyzer.update(p)
        self.assertEqual(res_reappear["queue_count"], 1)
        self.assertEqual(res_reappear["total_served"], 0)

    # --------------------------------------------------------------------------
    # Scenario 9: Missing tracking ID handling
    # --------------------------------------------------------------------------
    def test_09_missing_tracking_id(self):
        # Person detected inside queue without tracking ID (fallback -1)
        untracked_person = [{"id": -1, "bbox": [150, 150, 250, 250], "confidence": 0.85}]
        res = self.analyzer.update(untracked_person)
        # Still counted in queue_count for current frame
        self.assertEqual(res["queue_count"], 1)
        self.assertEqual(res["people"][0]["id"], -1)
        self.assertTrue(res["people"][0]["in_queue"])

    # --------------------------------------------------------------------------
    # Scenario 10: Person re-entering the queue
    # --------------------------------------------------------------------------
    def test_10_person_reentering_queue(self):
        p_in = [{"id": 11, "bbox": [150, 150, 250, 250], "confidence": 0.90}]
        p_out = [{"id": 11, "bbox": [20, 150, 80, 250], "confidence": 0.90}]

        # Enter queue
        res1 = self.analyzer.update(p_in)
        self.assertEqual(res1["queue_count"], 1)

        # Step out
        res2 = self.analyzer.update(p_out)
        self.assertEqual(res2["queue_count"], 0)

        # Re-enter queue
        res3 = self.analyzer.update(p_in)
        self.assertEqual(res3["queue_count"], 1)
        self.assertTrue(res3["people"][0]["in_queue"])

    # --------------------------------------------------------------------------
    # Scenario 11: Dwell-time and visit-history handling
    # --------------------------------------------------------------------------
    def test_11_dwell_time_handling(self):
        # Passerby cuts across queue for only 1 frame (< min_dwell = 3)
        passerby = [{"id": 12, "bbox": [150, 150, 250, 250], "confidence": 0.90}]
        self.analyzer.update(passerby)

        # Immediately enters service zone without dwell
        at_counter = [{"id": 12, "bbox": [320, 120, 380, 200], "confidence": 0.90}]
        res = self.analyzer.update(at_counter)

        # Must NOT count as served because dwell threshold was not met
        self.assertEqual(res["total_served"], 0)

    # --------------------------------------------------------------------------
    # Scenario 12: Reset between independent sessions
    # --------------------------------------------------------------------------
    def test_12_reset_between_independent_sessions(self):
        # Simulate activity
        p_in = [{"id": 15, "bbox": [150, 150, 250, 250], "confidence": 0.95}]
        for _ in range(4):
            self.analyzer.update(p_in)

        p_srv = [{"id": 15, "bbox": [320, 120, 380, 200], "confidence": 0.95}]
        self.analyzer.update(p_srv, timestamp_seconds=10.0)
        self.assertEqual(self.analyzer.total_served_count, 1)

        # Reset session
        self.analyzer.reset()
        self.assertEqual(self.analyzer.total_served_count, 0)
        self.assertEqual(len(self.analyzer.served_ids), 0)
        self.assertEqual(len(self.analyzer.track_history), 0)
        self.assertEqual(self.analyzer.frame_index, 0)

        # Fresh empty query
        fresh_res = self.analyzer.update([])
        self.assertEqual(fresh_res["queue_count"], 0)
        self.assertEqual(fresh_res["total_served"], 0)
        self.assertIsNone(fresh_res["service_rate"])

    # --------------------------------------------------------------------------
    # Scenario 13: Invalid or empty frame handling
    # --------------------------------------------------------------------------
    def test_13_invalid_or_empty_frame_handling(self):
        pipeline = QueueSensePipeline(roi_polygon=self.roi)
        # Test None frame
        res_none = pipeline.process_frame(None)
        self.assertEqual(res_none["queue_count"], 0)
        self.assertEqual(len(res_none["people"]), 0)

        # Test empty numpy array
        res_empty = pipeline.process_frame(np.zeros((0,), dtype=np.uint8))
        self.assertEqual(res_empty["queue_count"], 0)

        # Test 1D array
        res_1d = pipeline.process_frame(np.zeros((100,), dtype=np.uint8))
        self.assertEqual(res_1d["queue_count"], 0)

    # --------------------------------------------------------------------------
    # Scenario 14: Output contract fields and types
    # --------------------------------------------------------------------------
    def test_14_output_contract_fields_and_types(self):
        person = [{"id": 20, "bbox": [150, 150, 250, 250], "confidence": 0.91}]
        res = self.analyzer.update(person)

        self.assertIn("people", res)
        self.assertIn("queue_count", res)
        self.assertIn("service_rate", res)
        self.assertIn("total_served", res)

        self.assertIsInstance(res["people"], list)
        self.assertIsInstance(res["queue_count"], int)
        self.assertIsInstance(res["total_served"], int)
        self.assertTrue(res["service_rate"] is None or isinstance(res["service_rate"], float))

        p = res["people"][0]
        self.assertIsInstance(p["id"], int)
        self.assertIsInstance(p["bbox"], list)
        self.assertEqual(len(p["bbox"]), 4)
        for coord in p["bbox"]:
            self.assertIsInstance(coord, int)
        self.assertIsInstance(p["confidence"], float)
        self.assertIsInstance(p["in_queue"], bool)

    # --------------------------------------------------------------------------
    # Scenario 15: JSON serialization
    # --------------------------------------------------------------------------
    def test_15_json_serialization(self):
        person = [{"id": 30, "bbox": [150, 150, 250, 250], "confidence": 0.93}]
        res = self.analyzer.update(person)

        # Serialization to JSON string must not throw TypeError
        json_str = json.dumps(res)
        deserialized = json.loads(json_str)

        self.assertEqual(deserialized["queue_count"], res["queue_count"])
        self.assertEqual(deserialized["total_served"], res["total_served"])
        self.assertEqual(deserialized["service_rate"], res["service_rate"])
        self.assertEqual(len(deserialized["people"]), len(res["people"]))

    # --------------------------------------------------------------------------
    # Scenario 16: Zero or unavailable service rate
    # --------------------------------------------------------------------------
    def test_16_zero_or_unavailable_service_rate(self):
        # Case A: No service events observed -> service_rate is None (never misleading 0.0)
        res_no_data = self.analyzer.update([])
        self.assertIsNone(res_no_data["service_rate"])

        # Case B: Configurable manual fallback service rate
        analyzer_with_fallback = QueueAnalyzer(
            roi_polygon=self.roi,
            manual_service_rate=2.5
        )
        res_fallback = analyzer_with_fallback.update([])
        self.assertEqual(res_fallback["service_rate"], 2.5)

        # Case C: Automated rate when service events occur with sufficient time
        # Dwell 4 frames, move to service zone at t = 60s (1 person in 1 minute = 1.0/min)
        p_in = [{"id": 99, "bbox": [150, 150, 250, 250], "confidence": 0.95}]
        for i in range(4):
            self.analyzer.update(p_in, timestamp_seconds=i * 1.0)

        p_srv = [{"id": 99, "bbox": [320, 120, 380, 200], "confidence": 0.95}]
        res_calc = self.analyzer.update(p_srv, timestamp_seconds=60.0)
        self.assertEqual(res_calc["total_served"], 1)
        self.assertEqual(res_calc["service_rate"], 1.0)

    # --------------------------------------------------------------------------
    # Scenario 17: Invalid ROI configuration
    # --------------------------------------------------------------------------
    def test_17_invalid_roi_configuration(self):
        # Fewer than 3 points
        with self.assertRaises(ValueError):
            validate_polygon([(100, 100), (200, 200)])

        # None polygon
        with self.assertRaises(ValueError):
            validate_polygon(None)

        # Invalid coordinate structure
        with self.assertRaises(ValueError):
            validate_polygon([(100, 100, 50), (200, 200, 50), (300, 300, 50)])

        # Non-numeric coordinate
        with self.assertRaises(ValueError):
            validate_polygon([("abc", 100), (200, 200), (300, 300)])


if __name__ == "__main__":
    unittest.main()
