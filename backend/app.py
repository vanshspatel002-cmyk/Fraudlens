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
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "jfif", "png", "webp", "bmp", "tif", "tiff"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
REVERSE_SEARCH_KEY_ENV_NAMES = ("SERPAPI_KEY", "SERP_API_KEY", "SERPAPI_API_KEY")
GOOGLE_VISION_CREDENTIAL_ENV_NAMES = (
    "GOOGLE_CREDENTIALS_JSON",
    "GOOGLE_APPLICATION_CREDENTIALS_JSON",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GCP_SERVICE_ACCOUNT_JSON",
    "GOOGLE_CREDENTIALS_BASE64",
    "GOOGLE_APPLICATION_CREDENTIALS",
)
GOOGLE_VISION_SPLIT_ENV_NAMES = ("GOOGLE_PROJECT_ID", "GOOGLE_CLIENT_EMAIL", "GOOGLE_PRIVATE_KEY")
PUBLIC_BASE_URL_ENV_NAMES = (
    "PUBLIC_BASE_URL",
    "REVERSE_IMAGE_PUBLIC_BASE_URL",
    "RENDER_EXTERNAL_URL",
    "BACKEND_PUBLIC_URL",
    "BACKEND_API_URL",
    "API_BASE_URL",
)


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


def first_configured_env(names: tuple[str, ...]) -> str | None:
    return next((name for name in names if os.getenv(name, "").strip()), None)


def has_split_google_credentials() -> bool:
    return all(os.getenv(name, "").strip() for name in GOOGLE_VISION_SPLIT_ENV_NAMES)


def is_public_url(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith("https://") or normalized.startswith("http://")


def feature_diagnostics() -> dict:
    reverse_key = first_configured_env(REVERSE_SEARCH_KEY_ENV_NAMES)
    google_credential = first_configured_env(GOOGLE_VISION_CREDENTIAL_ENV_NAMES)
    public_base = first_configured_env(PUBLIC_BASE_URL_ENV_NAMES)
    public_base_value = os.getenv(public_base, "").strip() if public_base else ""
    google_ready = bool(google_credential or has_split_google_credentials())
    reverse_ready = bool(reverse_key)

    return {
        "reverseSearch": {
            "configured": reverse_ready,
            "status": "ready" if reverse_ready else "missing_api_key",
            "configuredEnv": reverse_key,
            "missingAnyOf": [] if reverse_ready else list(REVERSE_SEARCH_KEY_ENV_NAMES),
            "publicBaseConfiguredEnv": public_base,
            "publicBaseLooksValid": bool(public_base_value and is_public_url(public_base_value)),
            "message": (
                "Reverse search is configured."
                if reverse_ready
                else "Set SERPAPI_KEY on Render to enable reverse image search."
            ),
        },
        "googleVision": {
            "configured": google_ready,
            "status": "ready" if google_ready else "missing_credentials",
            "configuredEnv": google_credential or ("split_env_vars" if has_split_google_credentials() else None),
            "missingAnyOf": [] if google_ready else list(GOOGLE_VISION_CREDENTIAL_ENV_NAMES),
            "missingSplitEnvAlternative": [] if google_ready else list(GOOGLE_VISION_SPLIT_ENV_NAMES),
            "message": (
                "Google Vision credentials are configured."
                if google_ready
                else "Set GOOGLE_CREDENTIALS_JSON on Render to the full Google service-account JSON."
            ),
        },
    }


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
        "featureDiagnostics": feature_diagnostics(),
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
    diagnostics = feature_diagnostics()

    return jsonify(
        {
            "status": "working",
            "engine": "real-image-analyzer",
            "maxUploadMb": MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
            "allowedExtensions": sorted(ALLOWED_EXTENSIONS),
            "services": {
                "reverseSearchConfigured": diagnostics["reverseSearch"]["configured"],
                "googleVisionConfigured": diagnostics["googleVision"]["configured"],
                "publicImageBaseConfigured": bool(diagnostics["reverseSearch"]["publicBaseConfiguredEnv"]),
            },
            "featureDiagnostics": diagnostics,
        }
    )


@app.route("/api/diagnostics")
def diagnostics():
    return jsonify({"status": "working", "featureDiagnostics": feature_diagnostics()})


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
        return jsonify({"error": "Only JPG, JPEG, JFIF, PNG, WEBP, BMP, or TIFF files are allowed"}), 400

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
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
