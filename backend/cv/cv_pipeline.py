import os
import sys
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline import QueueSensePipeline
import config

QUEUE_ROI = config.DEFAULT_QUEUE_ROI
SERVICE_ZONE = config.DEFAULT_SERVICE_ZONE

_pipeline = QueueSensePipeline(
    roi_polygon=QUEUE_ROI,
    service_zone=SERVICE_ZONE,
    model_path=os.path.join(PROJECT_ROOT, "yolov8n.pt"),
    conf_thresh=0.35,
    manual_service_rate=2.0
)


def process_input(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError("Uploaded file was not found")

    extension = os.path.splitext(file_path)[1].lower()
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    video_extensions = {".mp4", ".mov", ".avi", ".mkv"}

    _pipeline.reset()

    if extension in image_extensions:
        frame = cv2.imread(file_path)
        if frame is None:
            raise ValueError("Could not read the uploaded image")

        return _pipeline.process_frame(frame)

    if extension in video_extensions:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            cap.release()
            raise ValueError("Could not open the uploaded video")

        result = None
        frame_count = 0
        max_frames = int(os.environ.get("QUEUESENSE_MAX_FRAMES", 60))
        try:
            while True:
                success, frame = cap.read()
                if not success:
                    break
                result = _pipeline.process_frame(frame)
                frame_count += 1
                if max_frames > 0 and frame_count >= max_frames:
                    break
        finally:
            cap.release()

        if result is None:
            raise ValueError("The uploaded video contains no readable frames")

        return result

    raise ValueError("Unsupported file type. Upload an image or video.")
