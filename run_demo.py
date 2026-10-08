"""
QueueSense Demo Runner
Runs the full pipeline on a video file or camera with visual debugging.

Usage:
    python run_demo.py --video sample_test.mp4
    python run_demo.py --video sample_test.mp4 --save output_demo.mp4 --no-window
    python run_demo.py --cam 0
"""

import argparse
import time
import cv2
import json

from pipeline import QueueSensePipeline
import config


def main():
    parser = argparse.ArgumentParser(description="QueueSense CV Demo Runner")
    parser.add_argument("--video", type=str, default="sample_test.mp4", help="Path to video file")
    parser.add_argument("--cam", type=int, default=None, help="Camera index for webcam stream")
    parser.add_argument("--save", type=str, default="output_demo.mp4", help="Path to save annotated video")
    parser.add_argument("--no-window", action="store_true", help="Run without opening GUI window (headless)")
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum frames to process")
    parser.add_argument("--conf", type=float, default=config.CONFIDENCE_THRESHOLD, help="Detection confidence")
    args = parser.parse_args()

    source = args.cam if args.cam is not None else args.video
    print(f"[QueueSense] Opening source: {source}")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[QueueSense] Video Info: {width}x{height} @ {fps:.1f} FPS, {total_frames} frames")

    # Define an ROI tailored to the video frame size
    # E.g., a rectangular queue area in the center-left where people walk
    roi = [
        (int(width * 0.15), int(height * 0.20)),
        (int(width * 0.70), int(height * 0.20)),
        (int(width * 0.70), int(height * 0.85)),
        (int(width * 0.15), int(height * 0.85))
    ]

    pipeline = QueueSensePipeline(roi_polygon=roi, conf_thresh=args.conf, fps=fps)

    # Video writer if saving
    writer = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.save, fourcc, fps, (width, height))
        print(f"[QueueSense] Saving output to: {args.save}")

    frame_idx = 0
    t_start = time.time()

    print("[QueueSense] Processing video stream...")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            if args.max_frames and frame_idx > args.max_frames:
                break

            # 1. Pipeline execution
            result = pipeline.process_frame(frame)

            # 2. Render visual debugging overlays
            annotated_frame = pipeline.render_debug_frame(frame, result)

            if writer:
                writer.write(annotated_frame)

            # Print periodic console update
            if frame_idx % 30 == 0 or frame_idx == 1:
                print(
                    f"Frame {frame_idx:04d}/{total_frames} | "
                    f"Queue Count: {result['queue_count']} | "
                    f"Service Rate: {result['service_rate']:.2f}/min | "
                    f"People: {len(result['people'])}"
                )

            # Interactive display
            if not args.no_window:
                cv2.imshow("QueueSense - Debug Monitor", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    print("[QueueSense] Stopped by user.")
                    break

    finally:
        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()

    elapsed = time.time() - t_start
    print(f"\n[QueueSense] Completed {frame_idx} frames in {elapsed:.2f}s ({frame_idx/max(elapsed, 0.001):.1f} FPS)")
    print(f"[QueueSense] Final Contract Result Sample:\n{json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
