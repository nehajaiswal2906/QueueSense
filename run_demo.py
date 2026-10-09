"""
QueueSense Demo Runner
Runs the full computer vision pipeline on a video file or camera with visual debugging.

Usage:
    python run_demo.py --video sample_test.mp4 --save output_demo.mp4 --no-window --max-frames 60
    python run_demo.py --video people_detection.mp4 --no-window
    python run_demo.py --cam 0
"""

import argparse
import os
import sys
import time
import json
import cv2

from pipeline import QueueSensePipeline
import config


def parse_args():
    parser = argparse.ArgumentParser(description="QueueSense Computer Vision Demo Runner (Team A)")
    parser.add_argument("--video", type=str, default="sample_test.mp4", help="Path to video file")
    parser.add_argument("--cam", type=int, default=None, help="Camera index for webcam stream")
    parser.add_argument("--save", type=str, default="output_demo.mp4", help="Path to save annotated video")
    parser.add_argument("--no-window", action="store_true", help="Run in headless mode without GUI window")
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum number of frames to process")
    parser.add_argument("--conf", type=float, default=config.CONFIDENCE_THRESHOLD, help="Detection confidence threshold")
    parser.add_argument("--manual-rate", type=float, default=None, help="Optional fallback manual service rate")
    return parser.parse_args()


def main():
    args = parse_args()

    # 1. Validate inputs and model
    if args.cam is None:
        if not os.path.exists(args.video):
            print(f"[ERROR] Video file not found: '{args.video}'")
            print("Please check the path or download a sample video.")
            sys.exit(1)
        source = args.video
        print(f"[QueueSense] Selected input video: {source}")
    else:
        source = args.cam
        print(f"[QueueSense] Selected camera index: {source}")

    if not os.path.exists(config.MODEL_PATH):
        print(f"[ERROR] Model weights not found at: '{config.MODEL_PATH}'")
        sys.exit(1)

    # 2. Open video stream
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Failed to open video source: {source}")
        sys.exit(1)

    raw_fps = cap.get(cv2.CAP_PROP_FPS)
    fps = raw_fps if (raw_fps is not None and raw_fps > 0) else 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if width <= 0 or height <= 0:
        print("[ERROR] Could not determine valid video frame dimensions.")
        cap.release()
        sys.exit(1)

    print(f"[QueueSense] Video Info: {width}x{height} @ {fps:.1f} FPS, total frames: {total_frames}")

    # 3. Configure Queue ROI (calibrated to frame dimensions)
    # Default: central queue area covering 50% width and 65% height
    roi = [
        (int(width * 0.15), int(height * 0.20)),
        (int(width * 0.70), int(height * 0.20)),
        (int(width * 0.70), int(height * 0.85)),
        (int(width * 0.15), int(height * 0.85))
    ]

    # Optional service counter zone near top-right of ROI
    service_zone = [
        (int(width * 0.65), int(height * 0.15)),
        (int(width * 0.85), int(height * 0.15)),
        (int(width * 0.85), int(height * 0.45)),
        (int(width * 0.65), int(height * 0.45))
    ]

    # 4. Initialize pipeline
    pipeline = QueueSensePipeline(
        roi_polygon=roi,
        service_zone=service_zone,
        conf_thresh=args.conf,
        fps=fps,
        manual_service_rate=args.manual_rate
    )
    print(f"[QueueSense] Pipeline initialized on device: {pipeline.device.upper()}")

    # 5. Set up VideoWriter if saving
    writer = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.save, fourcc, fps, (width, height))
        if not writer.isOpened():
            print(f"[WARNING] VideoWriter could not open '{args.save}'. Video will not be saved.")
            writer = None
        else:
            print(f"[QueueSense] Saving annotated video to: {args.save}")

    frame_idx = 0
    latest_result = None
    t_start = time.time()

    print("[QueueSense] Processing video stream...")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            if args.max_frames and frame_idx > args.max_frames:
                break

            # Pipeline execution
            latest_result = pipeline.process_frame(frame)

            # Visual overlay
            annotated_frame = pipeline.render_debug_frame(frame, latest_result)

            if writer:
                writer.write(annotated_frame)

            # Periodic log update
            if frame_idx % 20 == 0 or frame_idx == 1:
                svc_str = (
                    f"{latest_result['service_rate']:.2f}/min"
                    if latest_result["service_rate"] is not None
                    else "N/A"
                )
                print(
                    f"Frame {frame_idx:04d}/{total_frames} | "
                    f"Queue Count: {latest_result['queue_count']} | "
                    f"Total Served: {latest_result['total_served']} | "
                    f"Service Rate: {svc_str} | "
                    f"People: {len(latest_result['people'])}"
                )

            # GUI display if not headless
            if not args.no_window:
                cv2.imshow("QueueSense - Debug Monitor", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    print("[QueueSense] User stopped execution.")
                    break

    finally:
        cap.release()
        if writer:
            writer.release()
        if not args.no_window:
            cv2.destroyAllWindows()

    elapsed = time.time() - t_start

    # Check zero-frame failure condition
    if frame_idx == 0:
        print("[ERROR] Zero frames were processed. Pipeline run failed.")
        sys.exit(1)

    avg_fps = frame_idx / max(elapsed, 0.001)

    print("\n" + "=" * 60)
    print("QUEUESENSE RUN SUMMARY")
    print("=" * 60)
    print(f"Input source      : {source}")
    print(f"Processing device : {pipeline.device.upper()}")
    print(f"Frames processed  : {frame_idx}")
    print(f"Elapsed time      : {elapsed:.2f}s (Average Speed: {avg_fps:.1f} FPS)")
    if latest_result is not None:
        print(f"Final queue count : {latest_result['queue_count']}")
        print(f"Total served      : {latest_result['total_served']}")
        svc_str = (
            f"{latest_result['service_rate']:.2f} people/min"
            if latest_result["service_rate"] is not None
            else "Unavailable (Insufficient service events / observation time)"
        )
        print(f"Service rate      : {svc_str}")

    if args.save and os.path.exists(args.save):
        out_size_mb = os.path.getsize(args.save) / (1024 * 1024)
        print(f"Output video path : {args.save} ({out_size_mb:.2f} MB)")
        # Quick sanity check on reopening the saved video
        test_cap = cv2.VideoCapture(args.save)
        can_read = test_cap.isOpened()
        test_cap.release()
        print(f"Output valid      : {'VERIFIED (playable)' if can_read and out_size_mb > 0 else 'UNVERIFIED'}")
    print("=" * 60)

    if latest_result is not None:
        print(f"\nSample Output Contract:\n{json.dumps(latest_result, indent=2)}")


if __name__ == "__main__":
    main()
