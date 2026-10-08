"""
Test script for Phase 1 (YOLO detection) and Phase 2 (Tracking IDs)
"""

import cv2
from detector import PersonTracker

def main():
    tracker = PersonTracker(model_path="yolov8n.pt", conf_thresh=0.35)
    cap = cv2.VideoCapture("sample_test.mp4")

    if not cap.isOpened():
        print("ERROR: Could not open sample_test.mp4")
        return

    frame_count = 0
    max_frames = 30  # Test first 30 frames to verify detection and track consistency

    print(f"Testing YOLO detection and tracking on sample_test.mp4...")

    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        people = tracker.detect_and_track(frame, persist=True)
        
        # Display detection & tracking summary
        ids = [p["id"] for p in people]
        print(f"Frame {frame_count:02d}: Detected {len(people)} person(s) | IDs: {ids}")

    cap.release()
    print("Phase 1 & 2 verification complete.")

if __name__ == "__main__":
    main()
