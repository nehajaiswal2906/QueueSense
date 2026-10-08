"""
QueueSense - Multi-Scenario Verification Script
Executes the full pipeline on 3 different video scenarios:
1. Outdoor walkway / pedestrian flow (sample_test.mp4)
2. Retail / entrance corridor with crossing pedestrians (people_detection.mp4)
3. Indoor crowded room / hall (classroom.mp4)
"""

import sys
import os
import time
import cv2
import json

# Ensure parent directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import QueueSensePipeline


def test_scenario(video_path: str, max_frames: int = 60, scenario_name: str = ""):
    print(f"\n{'='*60}")
    print(f"RUNNING SCENARIO: {scenario_name} ({video_path})")
    print(f"{'='*60}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"FAILED to open {video_path}")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Custom ROI for this scenario: center 50% box
    roi = [
        (int(width * 0.20), int(height * 0.20)),
        (int(width * 0.80), int(height * 0.20)),
        (int(width * 0.80), int(height * 0.80)),
        (int(width * 0.20), int(height * 0.80))
    ]

    pipeline = QueueSensePipeline(roi_polygon=roi, conf_thresh=0.35, fps=fps)

    frames_processed = 0
    total_people_detected = 0
    max_queue_count = 0
    latest_result = None

    t0 = time.time()

    while cap.isOpened() and frames_processed < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        frames_processed += 1
        result = pipeline.process_frame(frame)
        latest_result = result

        # Verify output contract fields
        assert "people" in result, "Missing 'people' in contract"
        assert "queue_count" in result, "Missing 'queue_count' in contract"
        assert "service_rate" in result, "Missing 'service_rate' in contract"
        assert isinstance(result["people"], list), "'people' must be a list"
        assert isinstance(result["queue_count"], int), "'queue_count' must be int"
        assert isinstance(result["service_rate"], float), "'service_rate' must be float"

        # Contract person item check
        for p in result["people"]:
            assert "id" in p
            assert "bbox" in p
            assert "confidence" in p
            assert "in_queue" in p

        num_people = len(result["people"])
        total_people_detected += num_people
        max_queue_count = max(max_queue_count, result["queue_count"])

    cap.release()
    elapsed = time.time() - t0
    avg_fps = frames_processed / max(elapsed, 0.001)

    print(f"Results for {scenario_name}:")
    print(f"  - Frames Processed: {frames_processed}")
    print(f"  - Time Elapsed: {elapsed:.2f}s ({avg_fps:.1f} FPS)")
    print(f"  - Max Queue Count: {max_queue_count}")
    print(f"  - Avg People/Frame: {total_people_detected / max(frames_processed, 1):.2f}")
    print(f"  - Final Service Rate: {latest_result['service_rate']:.2f} people/min")
    print(f"  - Contract Validated: 100% compliant")
    return True


def main():
    scenarios = [
        ("sample_test.mp4", 50, "Scenario 1: Pedestrian Walkway"),
        ("people_detection.mp4", 50, "Scenario 2: Corridor / Entrance Stream"),
        ("classroom.mp4", 40, "Scenario 3: Indoor Crowded Room")
    ]

    all_passed = True
    for path, frames, name in scenarios:
        success = test_scenario(path, max_frames=frames, scenario_name=name)
        if not success:
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("ALL 3 SCENARIOS SUCCESSFULLY TESTED & VALIDATED!")
    else:
        print("ONE OR MORE SCENARIOS FAILED!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
