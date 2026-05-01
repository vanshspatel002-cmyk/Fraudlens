import os
from pathlib import Path
from uuid import uuid4

from analyzer import AnalysisError, analyze_image, apply_reverse_search_to_result, clamp
from flask import Flask, jsonify, request, send_from_directory, url_for
from flask_cors import CORS
from reverse_search import reverse_image_search
from vision_analyzer import analyze_google_vision
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


def load_local_env() -> None:
    for env_path in (BASE_DIR.parent / ".env", BASE_DIR.parent.parent / ".env"):
        if not env_path.exists():
            continue

        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip().lstrip("\ufeff")

            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


load_local_env()

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def round_metric(value: float) -> int:
    return int(round(clamp(value)))


def frontend_payload(result):
    metrics = result["metrics"]
    ela_manipulation_risk = metrics.get(
        "elaManipulationRisk",
        100.0 - metrics["compression"],
    )
    compression_artifact_risk = metrics.get(
        "elaArtifactRisk",
        100.0 - metrics["compression"],
    )
    noise_irregularity = metrics.get("noiseInconsistencyScore", 100.0 - metrics["noiseConsistency"])
    edge_inconsistency = 100.0 - metrics["edgeDensity"]
    color_artificiality = 100.0 - metrics["colorNaturalness"]
    blur_risk = max(0.0, 45.0 - metrics["sharpness"]) * 1.6

    ai_like_probability = metrics.get(
        "aiLikeProbability",
        clamp(
            metrics["screenshotProbability"] * 0.35
            + noise_irregularity * 0.22
            + color_artificiality * 0.18
            + ela_manipulation_risk * 0.15
            + edge_inconsistency * 0.06
            + blur_risk * 0.04
        ),
    )

    return {
        **result,
        "aiProb": round_metric(ai_like_probability),
        "forgery": {
            "compression": round_metric(ela_manipulation_risk),
            "sharpness": round_metric(metrics["sharpness"]),
            "edgeConsistency": round_metric(metrics["edgeDensity"]),
            "noiseIrregularity": round_metric(noise_irregularity),
            "compressionArtifacts": round_metric(compression_artifact_risk),
        },
    }


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")

    if value.endswith("/api"):
        value = value[:-4]

    return value


def public_image_url(filename: str) -> str:
    public_base_url = next(
        (
            normalize_base_url(value)
            for value in (
                os.getenv("PUBLIC_BASE_URL", ""),
                os.getenv("REVERSE_IMAGE_PUBLIC_BASE_URL", ""),
                os.getenv("RENDER_EXTERNAL_URL", ""),
                os.getenv("BACKEND_PUBLIC_URL", ""),
                os.getenv("BACKEND_API_URL", ""),
                os.getenv("API_BASE_URL", ""),
            )
            if normalize_base_url(value)
        ),
        "",
    )

    if public_base_url:
        return f"{public_base_url}/api/reverse-image/{filename}"

    return url_for("serve_reverse_image", filename=filename, _external=True)


@app.route("/api/health")
def health():
    return jsonify(
        {
            "status": "working",
            "engine": "real-image-analyzer",
            "maxUploadMb": MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
            "allowedExtensions": sorted(ALLOWED_EXTENSIONS),
            "services": {
                "reverseSearchConfigured": bool(
                    os.getenv("SERPAPI_KEY", "").strip()
                    or os.getenv("SERP_API_KEY", "").strip()
                    or os.getenv("SERPAPI_API_KEY", "").strip()
                ),
                "googleVisionConfigured": bool(
                    os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
                    or os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
                    or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
                    or os.getenv("GCP_SERVICE_ACCOUNT_JSON", "").strip()
                    or os.getenv("GOOGLE_CREDENTIALS_BASE64", "").strip()
                    or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
                ),
                "publicImageBaseConfigured": bool(
                    os.getenv("PUBLIC_BASE_URL", "").strip()
                    or os.getenv("REVERSE_IMAGE_PUBLIC_BASE_URL", "").strip()
                    or os.getenv("RENDER_EXTERNAL_URL", "").strip()
                    or os.getenv("BACKEND_PUBLIC_URL", "").strip()
                    or os.getenv("BACKEND_API_URL", "").strip()
                    or os.getenv("API_BASE_URL", "").strip()
                ),
            },
        }
    )


@app.route("/api/reverse-image/<path:filename>")
def serve_reverse_image(filename):
    safe_name = secure_filename(filename)

    if safe_name != filename or not allowed_file(safe_name):
        return jsonify({"error": "Invalid image path"}), 404

    return send_from_directory(UPLOAD_FOLDER, safe_name)


@app.route("/api/analyze", methods=["POST"])
def analyze():
    print("[api] analyze endpoint hit")

    if request.content_length and request.content_length > MAX_UPLOAD_SIZE_BYTES:
        return jsonify({"error": "Image is too large. Maximum size is 10 MB."}), 413

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only JPG, JPEG, PNG, WEBP, BMP, or TIFF files are allowed"}), 400

    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid4().hex}.{extension}"
    filepath = UPLOAD_FOLDER / filename
    file.save(filepath)

    try:
        result = analyze_image(filepath)
        google_vision = analyze_google_vision(filepath)
        result["googleVision"] = google_vision
        print(f"[api] googleVision available={google_vision['available']}")
        reverse_search = reverse_image_search(filepath, public_image_url(filename))
        result = apply_reverse_search_to_result(result, reverse_search)
        payload = frontend_payload(result)
        print(
            f"[api] analyzed {original_filename}: "
            f"score={payload['score']} riskLevel={payload['riskLevel']} aiProb={payload['aiProb']}"
        )
        return jsonify(payload)
    except AnalysisError as e:
        print("[api] analysis error:", str(e))
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print("[api] unexpected error:", str(e))
        return jsonify({"error": "Image analysis failed", "details": str(e)}), 500
    finally:
        try:
            filepath.unlink(missing_ok=True)
        except OSError as exc:
            print("[api] could not remove upload:", str(exc))

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG") == "1",
        port=int(os.getenv("PORT", "5000")),
    )
