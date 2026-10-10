
from flask import Flask, request
from flask_cors import CORS
from werkzeug.utils import secure_filename
import math
import os
import tempfile

from .intelligence import calculate_waiting_time, get_queue_status
from .cv.cv_pipeline import process_input

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "uploads"
)
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp",
    ".mp4", ".mov", ".avi", ".mkv"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def is_valid_number(value):
    """Accept finite numeric values, but reject booleans."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def build_result(queue_count, service_rate):
    """Build a consistent, understandable API response."""
    status = get_queue_status(queue_count)
    waiting_time = calculate_waiting_time(queue_count, service_rate)

    if status == "unknown":
        message = "Queue count is invalid; results are unavailable."
    elif waiting_time is None:
        message = (
            f"Queue status is {status}. "
            "Waiting time is unavailable because the service rate "
            "is missing or invalid."
        )
    else:
        message = (
            f"Queue status is {status}. "
            f"Estimated waiting time is {waiting_time} minutes."
        )

    return {
        "queue_count": queue_count,
        "service_rate": service_rate,
        "estimated_wait": waiting_time,
        "status": status,
        "density": status,
        "message": message,
    }


@app.route("/", methods=["GET"])
def home():
    return {
        "message": "QueueSense backend is running.",
        "available_endpoints": [
            "GET /health",
            "GET /mock",
            "POST /analyze",
            "POST /upload",
        ],
    }


@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy", "message": "Backend is ready."}


@app.route("/mock", methods=["GET"])
def mock_analysis():
    return build_result(queue_count=8, service_rate=2.0)


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return {"error": "No file provided. Include a file field."}, 400

    file = request.files["file"]

    if not file.filename:
        return {"error": "No file selected."}, 400

    safe_filename = secure_filename(file.filename)
    extension = os.path.splitext(safe_filename)[1].lower()

    if not safe_filename or extension not in ALLOWED_EXTENSIONS:
        return {
            "error": "Unsupported file type. Upload an image or video."
        }, 400

    file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=app.config["UPLOAD_FOLDER"],
            suffix=extension,
            delete=False,
        ) as temp_file:
            file_path = temp_file.name
            file.save(temp_file)

        cv_result = process_input(file_path)

        if not isinstance(cv_result, dict):
            return {"error": "CV pipeline returned an invalid result."}, 502

        if "queue_count" not in cv_result:
            return {"error": "CV result is missing queue_count."}, 502

        if "service_rate" not in cv_result:
            return {"error": "CV result is missing service_rate."}, 502

        queue_count = cv_result["queue_count"]
        service_rate = cv_result["service_rate"]

        if not is_valid_number(queue_count) or queue_count < 0:
            return {
                "error": "CV pipeline returned an invalid queue_count."
            }, 502

        if service_rate is not None:
            if not is_valid_number(service_rate) or service_rate <= 0:
                service_rate = None

        return build_result(queue_count, service_rate)

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
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "error": "Request body must be a valid JSON object."
        }, 400

    if "queue_count" not in data:
        return {"error": "queue_count is required."}, 400

    if "service_rate" not in data:
        return {"error": "service_rate is required."}, 400

    queue_count = data["queue_count"]
    service_rate = data["service_rate"]

    if not is_valid_number(queue_count):
        return {"error": "queue_count must be a valid number."}, 400

    if queue_count < 0:
        return {"error": "queue_count cannot be negative."}, 400

    if not is_valid_number(service_rate):
        return {"error": "service_rate must be a valid number."}, 400

    if service_rate <= 0:
        return {"error": "service_rate must be greater than zero."}, 400

    return build_result(queue_count, service_rate)


if __name__ == "__main__":
    app.run(debug=True)