"""
Test script for Phase 1 (YOLO detection) and Phase 2 (Tracking IDs)
"""

import os
import cv2
from detector import PersonTracker


def main():
    tracker = PersonTracker(model_path="yolov8n.pt", conf_thresh=0.35)
    video_file = "people_detection.mp4" if os.path.exists("people_detection.mp4") else "sample_test.mp4"

    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"ERROR: Could not open {video_file}")
        return

    frame_count = 0
    max_frames = 50

    print(f"Testing YOLO detection and tracking on {video_file} (device: {tracker.device.upper()})...")

    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        people = tracker.detect_and_track(frame, persist=True)
        
        # Display detection & tracking summary
        ids = [p["id"] for p in people]
        if frame_count % 10 == 0 or len(people) > 0:
            print(f"Frame {frame_count:02d}: Detected {len(people)} person(s) | IDs: {ids}")

    cap.release()
    print("Phase 1 & 2 verification complete.")


if __name__ == "__main__":
    main()
