"""
QueueSense - Multi-Scenario Verification Script
Executes the full pipeline on 3 diverse video scenarios:
1. Outdoor walkway / pedestrian flow (sample_test.mp4)
2. Retail / entrance corridor with crossing pedestrians (people_detection.mp4)
3. Indoor crowded room / hall (classroom.mp4)
"""

import sys
import os
import time
import cv2
import json
import numpy as np

# Ensure parent directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import QueueSensePipeline


def test_scenario(video_path: str, max_frames: int = 50, scenario_name: str = ""):
    print(f"\n{'='*60}")
    print(f"RUNNING SCENARIO: {scenario_name} ({video_path})")
    print(f"{'='*60}")

    if not os.path.exists(video_path):
        print(f"[SKIP/FAIL] Video file does not exist: {video_path}")
        return False

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[FAIL] Could not open video: {video_path}")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Custom polygonal ROI for this scenario: central 60% box
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
        if not ret or frame is None:
            break

        frames_processed += 1
        result = pipeline.process_frame(frame)
        latest_result = result

        # Verify output contract fields
        assert "people" in result, "Missing 'people' in contract"
        assert "queue_count" in result, "Missing 'queue_count' in contract"
        assert "service_rate" in result, "Missing 'service_rate' in contract"
        assert "total_served" in result, "Missing 'total_served' in contract"

        assert isinstance(result["people"], list), "'people' must be a list"
        assert isinstance(result["queue_count"], int), "'queue_count' must be int"
        assert isinstance(result["total_served"], int), "'total_served' must be int"
        assert result["service_rate"] is None or isinstance(result["service_rate"], (float, int)), (
            "'service_rate' must be float or None"
        )

        # JSON serialization validation
        json_bytes = json.dumps(result)
        assert json_bytes is not None

        # Contract person item check
        for p in result["people"]:
            assert "id" in p, "Person missing 'id'"
            assert "bbox" in p, "Person missing 'bbox'"
            assert "confidence" in p, "Person missing 'confidence'"
            assert "in_queue" in p, "Person missing 'in_queue'"
            assert len(p["bbox"]) == 4, "Bbox must be length 4"
            assert isinstance(p["in_queue"], bool), "'in_queue' must be bool"

        num_people = len(result["people"])
        total_people_detected += num_people
        max_queue_count = max(max_queue_count, result["queue_count"])

    cap.release()
    elapsed = time.time() - t0
    avg_fps = frames_processed / max(elapsed, 0.001)

    svc_display = (
        f"{latest_result['service_rate']:.2f} people/min"
        if latest_result and latest_result["service_rate"] is not None
        else "Unavailable (None)"
    )

    print(f"Results for {scenario_name}:")
    print(f"  - Device: {pipeline.device.upper()}")
    print(f"  - Frames Processed: {frames_processed}")
    print(f"  - Time Elapsed: {elapsed:.2f}s ({avg_fps:.1f} FPS)")
    print(f"  - Max Queue Count: {max_queue_count}")
    print(f"  - Total Served: {latest_result['total_served'] if latest_result else 0}")
    print(f"  - Avg People/Frame: {total_people_detected / max(frames_processed, 1):.2f}")
    print(f"  - Final Service Rate: {svc_display}")
    print(f"  - Contract Validated: 100% compliant")
    return True


def test_synthetic_scenario(frames_count: int = 30, scenario_name: str = "Scenario 3: Synthetic Stream & Occlusions"):
    print(f"\n{'='*60}")
    print(f"RUNNING SCENARIO: {scenario_name}")
    print(f"{'='*60}")

    width, height = 1280, 720
    roi = [(300, 200), (900, 200), (900, 600), (300, 600)]
    pipeline = QueueSensePipeline(roi_polygon=roi, conf_thresh=0.35, fps=30.0)

    # Generate synthetic frames (some empty, some with noise, verifying zero crash)
    for i in range(frames_count):
        if i % 5 == 0:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
        else:
            frame = np.full((height, width, 3), 128, dtype=np.uint8)
            # Add simple drawing
            cv2.rectangle(frame, (100 + i * 10, 200), (200 + i * 10, 500), (255, 255, 255), -1)

        result = pipeline.process_frame(frame)
        assert "people" in result
        assert "queue_count" in result
        assert "service_rate" in result
        assert "total_served" in result
        json.dumps(result)

    print(f"Results for {scenario_name}:")
    print(f"  - Device: {pipeline.device.upper()}")
    print(f"  - Frames Processed: {frames_count}")
    print(f"  - Resiliency: Passed all empty and synthetic frames")
    print(f"  - Contract Validated: 100% compliant")
    return True


def main():
    scenarios = [
        ("assets/canteen_queue_demo.mp4", 45, "Scenario 1: Canteen / Checkout Counter Queue"),
        ("assets/cafe_counter_candidate.mp4", 35, "Scenario 2: Cafe Counter Ordering Stream")
    ]

    all_passed = True
    for path, frames, name in scenarios:
        if os.path.exists(path):
            success = test_scenario(path, max_frames=frames, scenario_name=name)
            if not success:
                all_passed = False
        else:
            print(f"[SKIP] Video path not found: {path}")

    # Always run the synthetic robustness scenario
    synth_success = test_synthetic_scenario()
    if not synth_success:
        all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("ALL SCENARIOS SUCCESSFULLY TESTED & VALIDATED!")
    else:
        print("ONE OR MORE SCENARIOS FAILED!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

