from flask import Flask, request
from werkzeug.utils import secure_filename
import os
import tempfile

from .intelligence import calculate_waiting_time, get_queue_status
from .cv.cv_pipeline import process_input

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".mp4", ".mov", ".avi", ".mkv"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def home():
    return {
        "message": "QueueSense backend is running"
    }


@app.route("/health")
def health():
    return {
        "status": "healthy"
    }

@app.route("/mock", methods=["GET"])
def mock_analysis():
    queue_count = 8
    service_rate = 2.0

    estimated_wait = calculate_waiting_time(
        queue_count,
        service_rate
    )

    status = get_queue_status(queue_count)

    return {
        "queue_count": queue_count,
        "service_rate": service_rate,
        "estimated_wait": estimated_wait,
        "status": status
    }
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return {"error": "No file provided"}, 400

    file = request.files["file"]

    if not file.filename:
        return {"error": "No file selected"}, 400

    safe_filename = secure_filename(file.filename)
    extension = os.path.splitext(safe_filename)[1].lower()

    if not safe_filename or extension not in ALLOWED_EXTENSIONS:
        return {"error": "Unsupported file type. Upload an image or video."}, 400

    file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=app.config["UPLOAD_FOLDER"],
            suffix=extension,
            delete=False
        ) as temp_file:
            file_path = temp_file.name
            file.save(temp_file)

        cv_result = process_input(file_path)
        queue_count = cv_result["queue_count"]
        service_rate = cv_result["service_rate"]

        estimated_wait = calculate_waiting_time(queue_count, service_rate)
        status = get_queue_status(queue_count)

        return {
            "queue_count": queue_count,
            "service_rate": service_rate,
            "estimated_wait": estimated_wait,
            "status": status
        }
    except (ValueError, FileNotFoundError) as error:
        return {"error": str(error)}, 400
    except Exception:
        app.logger.exception("Unexpected error while processing uploaded file")
        return {"error": "Could not process the uploaded file."}, 500
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()

    if not data:
        return {
            "error": "Request body must contain JSON data"
        }, 400

    if "queue_count" not in data:
        return {
            "error": "queue_count is required"
        }, 400

    if "service_rate" not in data:
        return {
            "error": "service_rate is required"
        }, 400

    queue_count = data["queue_count"]
    service_rate = data["service_rate"]

    if not isinstance(queue_count, (int, float)):
        return {
            "error": "queue_count must be a number"
        }, 400

    if not isinstance(service_rate, (int, float)):
        return {
            "error": "service_rate must be a number"
        }, 400

    if queue_count < 0:
        return {
            "error": "queue_count cannot be negative"
        }, 400

    if service_rate <= 0:
        return {
            "error": "service_rate must be greater than 0"
        }, 400

    waiting_time = calculate_waiting_time(queue_count, service_rate)
    status = get_queue_status(queue_count)

    return {
    "queue_count": queue_count,
    "service_rate": service_rate,
    "estimated_wait": waiting_time,
    "status": status
    }

if __name__ == "__main__":
    app.run(debug=True)