from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
from typing import Any

import cv2
import numpy as np
from PIL import ExifTags, Image

cv2.setNumThreads(1)

NOT_AVAILABLE = "Not available"
EDITING_SOFTWARE_KEYWORDS = (
    "adobe",
    "photoshop",
    "lightroom",
    "snapseed",
    "gimp",
    "canva",
    "picsart",
    "pixlr",
    "facetune",
    "affinity",
)
PRODUCT_LABEL_KEYWORDS = (
    "accessory",
    "appliance",
    "bag",
    "bicycle",
    "bike",
    "book",
    "bottle",
    "camera",
    "car",
    "chair",
    "clothing",
    "computer",
    "console",
    "couch",
    "desk",
    "dress",
    "electronics",
    "furniture",
    "game",
    "gadget",
    "handbag",
    "headphone",
    "jacket",
    "jeans",
    "keyboard",
    "laptop",
    "mobile",
    "monitor",
    "motorcycle",
    "phone",
    "product",
    "refrigerator",
    "shoe",
    "sofa",
    "speaker",
    "table",
    "tablet",
    "television",
    "tool",
    "toy",
    "vehicle",
    "watch",
)
KNOWN_BRAND_LOGOS = (
    "apple",
    "dell",
    "nike",
    "samsung",
    "hp",
    "hewlett-packard",
    "lenovo",
)
ELEVATED_SAFE_SEARCH = {"POSSIBLE", "LIKELY", "VERY_LIKELY"}


class AnalysisError(ValueError):
    """Raised when an uploaded file cannot be analyzed as an image."""


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return float(max(minimum, min(maximum, value)))


def normalize_range(value: float, low: float, high: float) -> float:
    """Map a measured value onto 0-100 using fixed deterministic thresholds."""
    if high <= low:
        raise ValueError("high must be greater than low")

    return clamp(((value - low) / (high - low)) * 100.0)


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()

    return str(value).strip()


def safe_number(value: Any) -> float | None:
    try:
        if hasattr(value, "numerator") and hasattr(value, "denominator"):
            denominator = float(value.denominator)

            if denominator == 0:
                return None

            return float(value.numerator) / denominator

        if isinstance(value, tuple) and len(value) == 2:
            denominator = float(value[1])

            if denominator == 0:
                return None

            return float(value[0]) / denominator

        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def json_safe(value: Any) -> Any:
    """Convert Pillow metadata values into JSON-friendly primitives."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="ignore").strip("\x00").strip()
        return text if text else value.hex()

    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        numeric = safe_number(value)
        return round(numeric, 8) if numeric is not None else clean_text(value)

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}

    return clean_text(value)


def first_text(*values: Any) -> str:
    for value in values:
        text = clean_text(value)

        if text:
            return text

    return ""


def extract_text_metadata(info: dict[str, Any]) -> dict[str, Any]:
    ignored_keys = {"exif", "icc_profile"}
    text_metadata: dict[str, Any] = {}

    for key, value in info.items():
        if key in ignored_keys:
            continue

        if isinstance(value, (str, bytes, int, float, bool, tuple, list, dict)):
            safe_value = json_safe(value)

            if safe_value not in ("", [], {}):
                text_metadata[str(key)] = safe_value

    return text_metadata


def extract_xmp_metadata(info: dict[str, Any]) -> dict[str, str]:
    xmp: dict[str, str] = {}

    for key, value in info.items():
        if "xmp" not in key.lower():
            continue

        text = clean_text(value)

        if text:
            xmp[str(key)] = text[:4000]

    return xmp


def gps_coordinate_to_decimal(value: Any, reference: Any) -> float | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None

    degrees = safe_number(value[0])
    minutes = safe_number(value[1])
    seconds = safe_number(value[2])

    if degrees is None or minutes is None or seconds is None:
        return None

    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    ref = clean_text(reference).upper()

    if ref in {"S", "W"}:
        decimal *= -1

    return round(decimal, 6)


def read_exif_values(exif: Image.Exif) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read standard EXIF plus nested EXIF/GPS/Interop IFDs from Pillow."""
    exif_values: dict[str, Any] = {}
    raw_ifds: dict[str, Any] = {}

    def add_tag(tag_id: int, value: Any, prefix: str = "") -> None:
        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
        key = f"{prefix}{tag_name}" if prefix else str(tag_name)
        exif_values[key] = json_safe(value)

    for tag_id, value in exif.items():
        add_tag(tag_id, value)

    ifd_specs = {
        "Exif": 0x8769,
        "GPS": 0x8825,
        "Interop": 0xA005,
    }

    for ifd_name, tag_id in ifd_specs.items():
        try:
            ifd = exif.get_ifd(tag_id)
        except (KeyError, TypeError, AttributeError, ValueError):
            ifd = {}

        if not ifd:
            continue

        readable_ifd: dict[str, Any] = {}

        for nested_tag_id, value in ifd.items():
            if ifd_name == "GPS":
                tag_name = ExifTags.GPSTAGS.get(nested_tag_id, nested_tag_id)
            else:
                tag_name = ExifTags.TAGS.get(nested_tag_id, nested_tag_id)

            readable_ifd[str(tag_name)] = json_safe(value)
            exif_values[str(tag_name)] = json_safe(value)

        raw_ifds[ifd_name] = readable_ifd

    return exif_values, raw_ifds


def load_image(path: str | Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)

    if image is None:
        raise AnalysisError("Uploaded file is not a readable image")

    return image


def extract_metadata(path: str | Path) -> dict[str, Any]:
    """Extract real image metadata from EXIF, nested IFDs, and container fields."""
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            width, height = image.size
            image_format = clean_text(image.format) or NOT_AVAILABLE
            mode = clean_text(image.mode) or NOT_AVAILABLE
            mime_type = clean_text(getattr(image, "get_format_mimetype", lambda: "")())
            info = dict(image.info)
            frame_count = getattr(image, "n_frames", 1)
            animated = bool(getattr(image, "is_animated", False))
    except Exception as exc:
        raise AnalysisError("Could not read image metadata") from exc

    exif_values, raw_ifds = read_exif_values(exif)
    text_metadata = extract_text_metadata(info)
    xmp_metadata = extract_xmp_metadata(info)
    make = first_text(exif_values.get("Make"), text_metadata.get("Make"))
    model = first_text(exif_values.get("Model"), text_metadata.get("Model"))
    camera = " ".join(part for part in (make, model) if part).strip() or NOT_AVAILABLE
    date_taken = (
        first_text(
            exif_values.get("DateTimeOriginal"),
            exif_values.get("DateTimeDigitized"),
            exif_values.get("DateTime"),
            text_metadata.get("Creation Time"),
            text_metadata.get("date:create"),
            text_metadata.get("date:modify"),
        )
        or NOT_AVAILABLE
    )
    software = (
        first_text(
            exif_values.get("Software"),
            text_metadata.get("Software"),
            text_metadata.get("software"),
            text_metadata.get("Application"),
        )
        or NOT_AVAILABLE
    )
    lens = first_text(exif_values.get("LensModel"), exif_values.get("LensMake")) or NOT_AVAILABLE
    orientation = exif_values.get("Orientation", NOT_AVAILABLE)
    dpi = info.get("dpi")
    icc_profile = info.get("icc_profile")
    gps_latitude = gps_coordinate_to_decimal(
        exif_values.get("GPSLatitude"),
        exif_values.get("GPSLatitudeRef"),
    )
    gps_longitude = gps_coordinate_to_decimal(
        exif_values.get("GPSLongitude"),
        exif_values.get("GPSLongitudeRef"),
    )
    gps_available = gps_latitude is not None and gps_longitude is not None
    exif_available = bool(exif_values)
    container_metadata_available = bool(text_metadata or xmp_metadata or dpi or icc_profile)

    return {
        "camera": camera,
        "date": date_taken,
        "software": software,
        "width": int(width),
        "height": int(height),
        "format": image_format,
        "mode": mode,
        "mimeType": mime_type or NOT_AVAILABLE,
        "megapixels": round((width * height) / 1_000_000, 2),
        "orientation": orientation,
        "lens": lens,
        "make": make or NOT_AVAILABLE,
        "model": model or NOT_AVAILABLE,
        "dateTaken": date_taken,
        "dpi": json_safe(dpi) if dpi else NOT_AVAILABLE,
        "colorProfilePresent": bool(icc_profile),
        "iccProfileBytes": len(icc_profile) if isinstance(icc_profile, bytes) else 0,
        "animated": animated,
        "frameCount": int(frame_count or 1),
        "gpsAvailable": gps_available,
        "gps": {
            "latitude": gps_latitude,
            "longitude": gps_longitude,
            "altitude": exif_values.get("GPSAltitude", NOT_AVAILABLE),
            "timestamp": first_text(exif_values.get("GPSTimeStamp"), exif_values.get("GPSDateStamp"))
            or NOT_AVAILABLE,
        },
        "exposure": {
            "exposureTime": exif_values.get("ExposureTime", NOT_AVAILABLE),
            "fNumber": exif_values.get("FNumber", NOT_AVAILABLE),
            "iso": exif_values.get("ISOSpeedRatings", exif_values.get("PhotographicSensitivity", NOT_AVAILABLE)),
            "focalLength": exif_values.get("FocalLength", NOT_AVAILABLE),
            "exposureProgram": exif_values.get("ExposureProgram", NOT_AVAILABLE),
            "flash": exif_values.get("Flash", NOT_AVAILABLE),
        },
        "metadataAvailable": exif_available or container_metadata_available,
        "exifAvailable": exif_available,
        "containerMetadataAvailable": container_metadata_available,
        "xmpAvailable": bool(xmp_metadata),
        "raw": {
            "exif": exif_values,
            "ifds": raw_ifds,
            "container": text_metadata,
            "xmp": xmp_metadata,
        },
    }


def to_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def calculate_sharpness(image: np.ndarray) -> tuple[float, dict[str, float]]:
    """Use Laplacian variance: low values are blurry, high values have detail."""
    gray = to_gray(image)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    score = min(100.0, laplacian_variance / 10.0)

    return round(clamp(score), 2), {
        "laplacianVariance": round(laplacian_variance, 4),
        "sharpnessRaw": round(laplacian_variance, 4),
        "sharpnessScore": round(clamp(score), 2),
    }


def calculate_metadata_integrity(metadata: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Score how much useful capture metadata is present and internally useful."""
    weighted_fields = [
        (metadata.get("camera") != NOT_AVAILABLE, 20.0),
        (metadata.get("date") != NOT_AVAILABLE, 15.0),
        (metadata.get("software") != NOT_AVAILABLE, 8.0),
        (metadata.get("lens") != NOT_AVAILABLE, 8.0),
        (metadata.get("exifAvailable") is True, 18.0),
        (metadata.get("containerMetadataAvailable") is True, 8.0),
        (metadata.get("colorProfilePresent") is True, 5.0),
        (metadata.get("gpsAvailable") is True, 4.0),
    ]
    exposure = metadata.get("exposure", {})

    if isinstance(exposure, dict):
        weighted_fields.extend(
            [
                (exposure.get("exposureTime") != NOT_AVAILABLE, 4.0),
                (exposure.get("fNumber") != NOT_AVAILABLE, 4.0),
                (exposure.get("iso") != NOT_AVAILABLE, 3.0),
                (exposure.get("focalLength") != NOT_AVAILABLE, 3.0),
            ]
        )

    completeness = sum(weight for present, weight in weighted_fields if present)
    editing_software = 100.0 if is_editing_software_detected(metadata) else 0.0
    dimensions_present = float(metadata.get("width", 0) > 0 and metadata.get("height", 0) > 0)
    integrity_score = clamp(completeness - (editing_software * 0.08))

    return round(integrity_score, 2), {
        "metadataCompleteness": round(clamp(completeness), 2),
        "metadataEditingSoftwareRisk": editing_software,
        "metadataDimensionsPresent": dimensions_present,
        "metadataExifPresent": float(metadata.get("exifAvailable") is True),
        "metadataContainerPresent": float(metadata.get("containerMetadataAvailable") is True),
    }


def calculate_local_blur_consistency(image: np.ndarray) -> dict[str, float]:
    gray = to_gray(image)
    block_size = 64
    height, width = gray.shape
    values: list[float] = []

    for y in range(0, height - block_size + 1, block_size):
        for x in range(0, width - block_size + 1, block_size):
            block = gray[y : y + block_size, x : x + block_size]
            values.append(float(cv2.Laplacian(block, cv2.CV_64F).var()))

    if not values:
        values = [float(cv2.Laplacian(gray, cv2.CV_64F).var())]

    block_values = np.array(values, dtype=np.float32)
    mean_value = float(np.mean(block_values)) + 1e-6
    coefficient_variation = float(np.std(block_values) / mean_value)
    local_blur_risk = normalize_range(coefficient_variation, low=0.65, high=2.2)

    return {
        "localSharpnessMean": round(float(np.mean(block_values)), 4),
        "localSharpnessCoefficientVariation": round(coefficient_variation, 4),
        "localBlurInconsistencyRisk": round(local_blur_risk, 4),
    }


def resize_for_ela(image: Image.Image, max_dimension: int = 1600) -> Image.Image:
    width, height = image.size
    largest = max(width, height)

    if largest <= max_dimension:
        return image.copy()

    scale = max_dimension / largest
    next_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(next_size, Image.Resampling.LANCZOS)


def jpeg_recompressed_array(image: Image.Image, quality: int) -> np.ndarray:
    output = BytesIO()
    image.save(output, format="JPEG", quality=int(quality), optimize=False)
    output.seek(0)

    with Image.open(output) as recompressed:
        return np.asarray(recompressed.convert("RGB"), dtype=np.int16)


def estimate_jpeg_quality(image: Image.Image, original_array: np.ndarray) -> tuple[int, float]:
    """Approximate source JPEG quality by finding the lowest recompression error."""
    candidate_qualities = [55, 60, 65, 70, 75, 80, 85, 88, 90, 92, 94, 96, 98]
    best_quality = 90
    best_error = float("inf")

    for quality in candidate_qualities:
        recompressed_array = jpeg_recompressed_array(image, quality)
        error = float(np.mean(np.abs(original_array - recompressed_array)))

        if error < best_error:
            best_quality = quality
            best_error = error

    return best_quality, best_error


def block_means(diff_luma: np.ndarray) -> np.ndarray:
    height, width = diff_luma.shape
    shortest = min(height, width)
    block_size = 32 if shortest < 900 else 48
    block_size = max(16, min(block_size, shortest))
    trimmed_height = (height // block_size) * block_size
    trimmed_width = (width // block_size) * block_size

    if trimmed_height == 0 or trimmed_width == 0:
        return np.array([float(np.mean(diff_luma))], dtype=np.float32)

    trimmed = diff_luma[:trimmed_height, :trimmed_width]
    blocks = trimmed.reshape(
        trimmed_height // block_size,
        block_size,
        trimmed_width // block_size,
        block_size,
    )
    return blocks.mean(axis=(1, 3)).astype(np.float32)


def calculate_compression_score(path: str | Path) -> tuple[float, dict[str, Any]]:
    """Run Error Level Analysis using quality-90 JPEG recompression."""
    temp_path: Path | None = None

    try:
        with Image.open(path) as image:
            original = image.convert("RGB")
            original_array = np.asarray(original, dtype=np.int16)

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            original.save(temp_path, format="JPEG", quality=90)

        with Image.open(temp_path) as recompressed:
            recompressed_array = np.asarray(recompressed.convert("RGB"), dtype=np.int16)
    except Exception as exc:
        raise AnalysisError("Could not calculate ELA recompression artifacts") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    diff = np.abs(original_array - recompressed_array).astype(np.float32)
    mean_error = float(np.mean(diff))
    max_error = float(np.max(diff))
    std_error = float(np.std(diff))
    ela_score = clamp(round((mean_error * 8.0) + (std_error * 2.0)))
    compression_score = 100.0 - ela_score

    if ela_score < 25:
        interpretation = "Low artifact evidence"
    elif ela_score <= 60:
        interpretation = "Moderate artifact evidence"
    else:
        interpretation = "High artifact evidence"

    return round(clamp(compression_score), 2), {
        "elaScore": round(ela_score, 2),
        "elaMeanError": round(mean_error, 4),
        "elaMaxError": round(max_error, 4),
        "elaStdError": round(std_error, 4),
        "elaInterpretation": interpretation,
        "elaTargetQuality": 90.0,
        "elaRisk": round(ela_score, 4),
        "elaGlobalArtifactRisk": round(ela_score, 4),
        "elaLocalizedManipulationRisk": round(ela_score, 4),
        "elaReliability": 100.0,
    }


def calculate_jpeg_block_artifacts(image: np.ndarray) -> tuple[float, dict[str, float]]:
    """Measure 8x8 grid discontinuities often introduced by JPEG compression."""
    gray = to_gray(image).astype(np.float32)
    height, width = gray.shape

    if height < 16 or width < 16:
        return 100.0, {
            "jpegBoundaryDiscontinuity": 0.0,
            "jpegInteriorDiscontinuity": 0.0,
            "jpegBlockArtifactRisk": 0.0,
        }

    vertical_diff = np.abs(np.diff(gray, axis=1))
    horizontal_diff = np.abs(np.diff(gray, axis=0))
    vertical_indices = np.arange(1, width)
    horizontal_indices = np.arange(1, height)
    vertical_boundary = vertical_diff[:, (vertical_indices % 8) == 0]
    vertical_interior = vertical_diff[:, (vertical_indices % 8) != 0]
    horizontal_boundary = horizontal_diff[(horizontal_indices % 8) == 0, :]
    horizontal_interior = horizontal_diff[(horizontal_indices % 8) != 0, :]
    boundary = float(np.mean(np.concatenate([vertical_boundary.reshape(-1), horizontal_boundary.reshape(-1)])))
    interior = float(np.mean(np.concatenate([vertical_interior.reshape(-1), horizontal_interior.reshape(-1)]))) + 1e-6
    boundary_ratio = boundary / interior
    block_risk = normalize_range(boundary_ratio, low=1.12, high=2.0)
    integrity_score = 100.0 - block_risk

    return round(clamp(integrity_score), 2), {
        "jpegBoundaryDiscontinuity": round(boundary, 4),
        "jpegInteriorDiscontinuity": round(interior, 4),
        "jpegBoundaryRatio": round(boundary_ratio, 4),
        "jpegBlockArtifactRisk": round(block_risk, 4),
    }


def calculate_copy_move_risk(image: np.ndarray) -> tuple[float, dict[str, float]]:
    """Rough ORB self-similarity check for duplicated regions within one image."""
    gray = to_gray(image)
    max_dimension = 900
    height, width = gray.shape

    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)
        gray = cv2.resize(gray, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
        height, width = gray.shape

    orb = cv2.ORB_create(nfeatures=900, fastThreshold=12)
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if descriptors is None or keypoints is None or len(keypoints) < 24:
        return 0.0, {
            "copyMoveKeypoints": float(len(keypoints) if keypoints else 0),
            "copyMoveSuspiciousMatches": 0.0,
            "copyMoveRisk": 0.0,
        }

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(descriptors, descriptors)
    suspicious = 0
    distances: list[float] = []

    for match in matches:
        if match.queryIdx == match.trainIdx:
            continue

        point_a = np.array(keypoints[match.queryIdx].pt)
        point_b = np.array(keypoints[match.trainIdx].pt)
        spatial_distance = float(np.linalg.norm(point_a - point_b))

        if spatial_distance < 48:
            continue

        if match.distance <= 28:
            suspicious += 1
            distances.append(float(match.distance))

    suspicious_pairs = suspicious / 2.0
    match_density = suspicious_pairs / max(len(keypoints), 1)
    copy_move_risk = clamp(
        normalize_range(suspicious_pairs, low=6.0, high=40.0) * 0.55
        + normalize_range(match_density, low=0.025, high=0.16) * 0.45
    )

    return round(copy_move_risk, 2), {
        "copyMoveKeypoints": float(len(keypoints)),
        "copyMoveSuspiciousMatches": round(suspicious_pairs, 2),
        "copyMoveMatchDensity": round(match_density, 4),
        "copyMoveMeanDescriptorDistance": round(float(np.mean(distances)) if distances else 0.0, 4),
        "copyMoveRisk": round(copy_move_risk, 4),
    }


def calculate_noise_consistency(image: np.ndarray) -> tuple[float, dict[str, Any]]:
    """Estimate whether noise is consistent across local image blocks."""
    gray = to_gray(image).astype(np.float32)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    noise = np.abs(gray - blurred)
    height, width = noise.shape
    block_size = 32 if min(height, width) < 1024 else 64
    block_stds: list[float] = []

    for y in range(0, height, block_size):
        for x in range(0, width, block_size):
            block = noise[y : min(y + block_size, height), x : min(x + block_size, width)]

            if block.size < 64:
                continue

            block_stds.append(float(np.std(block)))

    if not block_stds:
        block_stds = [float(np.std(noise))]

    block_values = np.array(block_stds, dtype=np.float32)
    mean_noise = float(np.mean(block_values))
    noise_variation = float(np.std(block_values))
    coefficient_variation = noise_variation / (mean_noise + 1e-6)
    noise_inconsistency_score = min(100.0, coefficient_variation * 100.0)
    noise_consistency = 100.0 - noise_inconsistency_score

    if noise_inconsistency_score <= 30:
        interpretation = "consistent noise"
    elif noise_inconsistency_score <= 60:
        interpretation = "moderate noise inconsistency"
    else:
        interpretation = "high noise inconsistency"

    return round(clamp(noise_consistency), 2), {
        "meanNoise": round(mean_noise, 4),
        "noiseVariation": round(noise_variation, 4),
        "blockNoiseCoefficientVariation": round(coefficient_variation, 6),
        "noiseInconsistencyScore": round(noise_inconsistency_score, 2),
        "noiseConsistency": round(clamp(noise_consistency), 2),
        "interpretation": interpretation,
        "noiseBlockSize": float(block_size),
        "noiseBlocksAnalyzed": float(len(block_values)),
    }


def calculate_edge_density(image: np.ndarray) -> tuple[float, dict[str, float]]:
    """Analyze edge structure with Gaussian blur and Canny detection."""
    gray = to_gray(image)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 100, 200)
    edge_density_percent = (float(np.count_nonzero(edges)) / max(float(edges.size), 1.0)) * 100.0
    edge_density_score = min(100.0, edge_density_percent * 10.0)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharpness_score = min(100.0, laplacian_variance / 10.0)

    if edge_density_score < 5:
        interpretation = "very low edge density: blurry / low detail"
    elif edge_density_score > 80:
        interpretation = "very high edge density: screenshot/text-heavy/overprocessed"
    else:
        interpretation = "balanced edge density: natural photo"

    return round(clamp(edge_density_score), 2), {
        "edgeDensityPercent": round(edge_density_percent, 4),
        "edgeDensityScore": round(clamp(edge_density_score), 2),
        "sharpnessRaw": round(laplacian_variance, 4),
        "sharpnessScore": round(clamp(sharpness_score), 2),
        "edgeInterpretation": interpretation,
        "edgeDensityRatio": round(edge_density_percent / 100.0, 6),
        "edgeDensityRisk": round(100.0 if edge_density_score < 5 or edge_density_score > 80 else 0.0, 4),
    }


def calculate_color_naturalness(image: np.ndarray) -> tuple[float, dict[str, float]]:
    """Score saturation and contrast extremes without inventing semantic labels."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation_mean = float(np.mean(hsv[:, :, 1]))
    saturation_std = float(np.std(hsv[:, :, 1]))
    gray = to_gray(image)
    contrast_std = float(np.std(gray))

    saturation_high_risk = normalize_range(saturation_mean, low=145.0, high=225.0)
    saturation_low_risk = 100.0 - normalize_range(saturation_mean, low=18.0, high=55.0)
    contrast_high_risk = normalize_range(contrast_std, low=88.0, high=125.0)
    contrast_low_risk = 100.0 - normalize_range(contrast_std, low=18.0, high=42.0)
    small = cv2.resize(image, (128, 128), interpolation=cv2.INTER_AREA)
    quantized = (small // 16).reshape(-1, 3)
    unique_colors = len({tuple(color) for color in quantized})
    unique_color_ratio = unique_colors / max(len(quantized), 1)
    palette_compression_risk = 100.0 - normalize_range(unique_color_ratio, low=0.08, high=0.42)
    clipped_dark_ratio = float(np.mean(gray <= 3))
    clipped_light_ratio = float(np.mean(gray >= 252))
    clipping_risk = normalize_range(clipped_dark_ratio + clipped_light_ratio, low=0.01, high=0.22)
    color_risk = clamp(
        max(saturation_high_risk, saturation_low_risk) * 0.55
        + max(contrast_high_risk, contrast_low_risk) * 0.25
        + palette_compression_risk * 0.12
        + clipping_risk * 0.08
    )
    score = 100.0 - color_risk

    return round(clamp(score), 2), {
        "saturationMean": round(saturation_mean, 4),
        "saturationStd": round(saturation_std, 4),
        "contrastStd": round(contrast_std, 4),
        "uniqueColorRatio": round(unique_color_ratio, 6),
        "paletteCompressionRisk": round(palette_compression_risk, 4),
        "clippedDarkRatio": round(clipped_dark_ratio, 6),
        "clippedLightRatio": round(clipped_light_ratio, 6),
        "clippingRisk": round(clipping_risk, 4),
    }


def calculate_screenshot_probability(
    image: np.ndarray,
    metadata: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    """Estimate screenshot probability from deterministic, measurable signals."""
    height, width = image.shape[:2]
    aspect_ratio = width / max(height, 1)
    image_format = metadata["format"].upper()
    metadata_available = bool(metadata.get("metadataAvailable"))
    has_camera = has_camera_metadata(metadata)

    gray = to_gray(image)
    known_phone_ratios = (9 / 16, 16 / 9, 9 / 19.5, 19.5 / 9, 9 / 20, 20 / 9)
    nearest_ratio_delta = min(abs(aspect_ratio - known_ratio) for known_ratio in known_phone_ratios)
    aspect_signal = nearest_ratio_delta <= 0.06

    edges = cv2.Canny(gray, 60, 160)
    canny_edge_density = float(np.count_nonzero(edges) / max(edges.size, 1))
    edge_density_score = normalize_range(canny_edge_density, low=0.04, high=0.16)
    edge_signal = edge_density_score > 70

    block_size = 64
    flat_blocks = 0
    total_blocks = 0

    for y in range(0, height, block_size):
        for x in range(0, width, block_size):
            block = gray[y : min(y + block_size, height), x : min(x + block_size, width)]

            if block.size < 64:
                continue

            total_blocks += 1

            if float(np.var(block)) < 64.0:
                flat_blocks += 1

    flat_region_ratio = flat_blocks / total_blocks if total_blocks else 0.0
    flat_signal = flat_region_ratio > 0.35
    format_signal = image_format == "PNG" and not metadata_available
    no_camera_signal = not has_camera
    software = clean_text(metadata.get("software")).lower()
    software_signal = any(
        keyword in software
        for keyword in (
            "screenshot",
            "screen shot",
            "screen capture",
            "snipping",
            "canva",
            "picsart",
            "photoshop",
            "gimp",
            "snapseed",
            "lightroom",
        )
    )

    probability = 0.0

    if format_signal:
        probability += 25.0

    if no_camera_signal:
        probability += 10.0

    if aspect_signal:
        probability += 15.0

    if edge_signal:
        probability += 20.0

    if flat_signal:
        probability += 20.0

    if software_signal:
        probability += 10.0

    probability = clamp(probability)

    if probability <= 35:
        interpretation = "unlikely screenshot"
    elif probability <= 65:
        interpretation = "possible screenshot"
    else:
        interpretation = "likely screenshot"

    return round(probability, 2), {
        "aspectRatio": round(aspect_ratio, 4),
        "screenshotAspectScore": 100.0 if aspect_signal else 0.0,
        "screenshotAspectSignal": aspect_signal,
        "screenshotNearestAspectDelta": round(nearest_ratio_delta, 6),
        "screenshotDimensionScore": 0.0,
        "flatRegionRatio": round(flat_region_ratio, 4),
        "screenshotFlatRegionScore": 100.0 if flat_signal else 0.0,
        "screenshotFlatRegionSignal": flat_signal,
        "screenshotFlatBlocks": float(flat_blocks),
        "screenshotTotalBlocks": float(total_blocks),
        "screenshotCannyEdgeDensity": round(canny_edge_density, 6),
        "screenshotEdgeDensityScore": round(edge_density_score, 4),
        "screenshotEdgeSignal": edge_signal,
        "screenshotFormatSignal": format_signal,
        "screenshotNoCameraSignal": no_camera_signal,
        "screenshotSoftwareSignal": software_signal,
        "screenshotInterpretation": interpretation,
        "screenshotUiStructureScore": round(probability, 4),
        "screenshotFileSignalScore": 100.0 if format_signal else 0.0,
        "screenshotTextComponentScore": 0.0,
        "screenshotLowPaletteScore": 100.0 if flat_signal else 0.0,
        "pngWithoutCamera": float(format_signal),
    }


def is_editing_software_detected(metadata: dict[str, Any]) -> bool:
    software = metadata["software"]

    if software == NOT_AVAILABLE:
        return False

    return any(keyword in software.lower() for keyword in EDITING_SOFTWARE_KEYWORDS)


def has_camera_metadata(metadata: dict[str, Any]) -> bool:
    return metadata["camera"] != NOT_AVAILABLE


def calculate_frequency_naturalness(image: np.ndarray) -> tuple[float, dict[str, float]]:
    """Use Fourier spectrum statistics to flag over-smooth or synthetic-looking texture."""
    gray = to_gray(image).astype(np.float32)
    gray = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    gray -= float(np.mean(gray))
    spectrum = np.fft.fftshift(np.fft.fft2(gray))
    magnitude = np.log1p(np.abs(spectrum))
    height, width = magnitude.shape
    yy, xx = np.indices((height, width))
    center_y, center_x = height / 2.0, width / 2.0
    radius = np.sqrt((yy - center_y) ** 2 + (xx - center_x) ** 2)
    max_radius = float(np.max(radius)) + 1e-6
    low_band = magnitude[radius < max_radius * 0.18]
    mid_band = magnitude[(radius >= max_radius * 0.18) & (radius < max_radius * 0.42)]
    high_band = magnitude[radius >= max_radius * 0.42]
    high_frequency_ratio = float(np.mean(high_band) / (np.mean(mid_band) + 1e-6))
    low_frequency_ratio = float(np.mean(low_band) / (np.mean(mid_band) + 1e-6))
    normalized = magnitude / (float(np.sum(magnitude)) + 1e-6)
    spectral_entropy = float(-np.sum(normalized * np.log2(normalized + 1e-12)))
    spectral_entropy_normalized = spectral_entropy / np.log2(normalized.size)
    high_frequency_risk = 100.0 - normalize_range(high_frequency_ratio, low=0.72, high=1.08)
    low_frequency_dominance_risk = normalize_range(low_frequency_ratio, low=1.15, high=2.6)
    entropy_risk = 100.0 - normalize_range(spectral_entropy_normalized, low=0.68, high=0.90)
    frequency_risk = clamp(
        high_frequency_risk * 0.45
        + low_frequency_dominance_risk * 0.25
        + entropy_risk * 0.30
    )
    score = 100.0 - frequency_risk

    return round(clamp(score), 2), {
        "frequencyHighRatio": round(high_frequency_ratio, 6),
        "frequencyLowRatio": round(low_frequency_ratio, 6),
        "spectralEntropyNormalized": round(float(spectral_entropy_normalized), 6),
        "frequencyTextureRisk": round(frequency_risk, 4),
    }


def calculate_ai_like_probability(
    metrics: dict[str, float],
    raw_metrics: dict[str, float],
) -> tuple[float, dict[str, float]]:
    """AI suspicion heuristic from deterministic image-processing signals."""
    noise_irregularity = metrics.get("noiseInconsistencyScore", 100.0 - metrics["noiseConsistency"])
    color_artificiality = 100.0 - metrics["colorNaturalness"]
    compression_artifact_risk = max(
        100.0 - metrics["compression"],
        metrics.get("elaManipulationRisk", 0.0),
        metrics.get("elaArtifactRisk", 0.0),
        metrics.get("jpegBlockArtifactRisk", 0.0),
    )
    screenshot_risk = metrics["screenshotProbability"]
    ai_like = clamp(
        screenshot_risk * 0.35
        + color_artificiality * 0.25
        + noise_irregularity * 0.25
        + compression_artifact_risk * 0.15
    )

    return round(ai_like, 2), {
        "aiSuspicionHeuristic": round(ai_like, 4),
        "aiSuspicionScreenshotContribution": round(screenshot_risk * 0.35, 4),
        "aiSuspicionColorContribution": round(color_artificiality * 0.25, 4),
        "aiSuspicionNoiseContribution": round(noise_irregularity * 0.25, 4),
        "aiSuspicionCompressionContribution": round(compression_artifact_risk * 0.15, 4),
    }


def default_reverse_search_result() -> dict[str, Any]:
    return {
        "available": False,
        "matchesFound": 0,
        "originalityScore": None,
        "stockPhotoDetected": False,
        "sources": [],
        "message": "Reverse image search not run.",
    }


def default_google_vision_result() -> dict[str, Any]:
    return {
        "available": False,
        "message": "Google Vision unavailable",
        "labels": [],
        "logos": [],
        "ocrText": "",
        "phoneNumbers": [],
        "webMatches": 0,
        "matchingPages": [],
        "objects": [],
        "safeSearch": {},
        "marketplaceSignals": {},
    }


def compression_artifact_risk(metrics: dict[str, float]) -> float:
    if "elaScore" in metrics:
        return clamp(metrics["elaScore"])

    return clamp(
        max(
            100.0 - metrics.get("compression", 100.0),
            metrics.get("elaManipulationRisk", 0.0),
            metrics.get("elaArtifactRisk", 0.0),
            metrics.get("jpegBlockArtifactRisk", 0.0),
        )
    )


def add_breakdown(
    breakdown: list[dict[str, Any]],
    factor: str,
    impact: int,
    reason: str,
) -> None:
    breakdown.append({"factor": factor, "impact": impact, "reason": reason})


def google_vision_ocr_stats(google_vision: dict[str, Any]) -> tuple[str, int, int]:
    ocr_text = clean_text(google_vision.get("ocrText"))
    word_count = len(ocr_text.split())
    return ocr_text, len(ocr_text), word_count


def is_low_ocr_text(google_vision: dict[str, Any]) -> bool:
    _, character_count, word_count = google_vision_ocr_stats(google_vision)
    return character_count <= 80 and word_count <= 12


def is_heavy_ocr_text(google_vision: dict[str, Any]) -> bool:
    _, character_count, word_count = google_vision_ocr_stats(google_vision)
    return character_count >= 160 or word_count >= 25


def is_product_like_description(description: Any) -> bool:
    text = clean_text(description).lower()
    return any(keyword in text for keyword in PRODUCT_LABEL_KEYWORDS)


def vision_score_percent(value: Any) -> float:
    numeric = safe_number(value) or 0.0

    if numeric <= 1.0:
        numeric *= 100.0

    return clamp(numeric)


def clear_product_labels(google_vision: dict[str, Any]) -> list[str]:
    matches: list[str] = []

    for item in google_vision.get("labels") or []:
        if not isinstance(item, dict):
            continue

        score = vision_score_percent(item.get("score"))

        if score >= 65 and is_product_like_description(item.get("description")):
            matches.append(clean_text(item.get("description")))

    for item in google_vision.get("objects") or []:
        if not isinstance(item, dict):
            continue

        score = vision_score_percent(item.get("score"))

        if score >= 65 and is_product_like_description(item.get("name")):
            matches.append(clean_text(item.get("name")))

    return [match for match in matches if match]


def detected_brand_logos(google_vision: dict[str, Any]) -> list[str]:
    logos: list[str] = []

    for item in google_vision.get("logos") or []:
        if not isinstance(item, dict):
            continue

        description = clean_text(item.get("description"))

        if not description:
            continue

        if vision_score_percent(item.get("score")) >= 65 or any(
            brand in description.lower() for brand in KNOWN_BRAND_LOGOS
        ):
            logos.append(description)

    return logos


def google_vision_signal(google_vision: dict[str, Any], key: str) -> bool:
    signals = google_vision.get("marketplaceSignals")
    return isinstance(signals, dict) and signals.get(key) is True


def google_vision_spoof_elevated(google_vision: dict[str, Any]) -> bool:
    safe_search = google_vision.get("safeSearch")

    if not isinstance(safe_search, dict):
        return False

    return clean_text(safe_search.get("spoof")).upper() in ELEVATED_SAFE_SEARCH


def build_professional_score(
    metadata: dict[str, Any],
    metrics: dict[str, float],
    reverse_search: dict[str, Any] | None = None,
    google_vision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reverse_search = reverse_search or default_reverse_search_result()
    google_vision = google_vision or default_google_vision_result()
    score = 85
    score_breakdown: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    recommendations: list[str] = [
        "Ask seller for a fresh live photo before payment.",
        "Ask for a handwritten date or name note beside the product.",
        "Ask for a short video showing the product from multiple angles.",
    ]

    add_breakdown(
        score_breakdown,
        "Base score",
        85,
        "Started from a neutral secondhand marketplace photo baseline.",
    )

    if has_camera_metadata(metadata):
        score += 5
        add_breakdown(
            score_breakdown,
            "Metadata",
            5,
            "Real camera make/model metadata is present.",
        )
    else:
        score -= 4
        add_breakdown(
            score_breakdown,
            "Metadata",
            -4,
            "No camera metadata found. This is common for marketplace/social media images, so only a small penalty was applied.",
        )
        findings.append(
            {
                "severity": "low",
                "title": "Camera metadata not available",
                "description": "No camera make/model metadata was found. This is common after social media or messaging app processing.",
            }
        )

    if is_editing_software_detected(metadata):
        score -= 12
        add_breakdown(
            score_breakdown,
            "Metadata",
            -12,
            f"Editing software metadata detected: {metadata['software']}. This is suspicious but not proof of fraud.",
        )
        findings.append(
            {
                "severity": "medium",
                "title": "Editing software detected",
                "description": f"Metadata references {metadata['software']}. This can indicate editing or normal export workflow.",
            }
        )

    sharpness = metrics.get("sharpnessScore", metrics["sharpness"])
    if sharpness < 20:
        score -= 10
        add_breakdown(
            score_breakdown,
            "Sharpness",
            -10,
            "Variance of Laplacian sharpness score is below 20, indicating very low detail.",
        )
        findings.append(
            {
                "severity": "medium",
                "title": "Low sharpness detected",
                "description": "The image is very blurry or low-detail, which can hide product condition.",
            }
        )
    elif sharpness <= 40:
        score -= 5
        add_breakdown(
            score_breakdown,
            "Sharpness",
            -5,
            "Variance of Laplacian sharpness score is between 20 and 40, indicating moderate blur.",
        )
    elif 45 <= sharpness <= 85:
        score += 3
        add_breakdown(
            score_breakdown,
            "Sharpness",
            3,
            "Variance of Laplacian sharpness score is in a healthy range for visual inspection.",
        )

    artifact_risk = compression_artifact_risk(metrics)
    if artifact_risk > 60:
        score -= 15
        add_breakdown(
            score_breakdown,
            "Compression / ELA",
            -15,
            "ELA shows high recompression/editing indicators after quality-90 JPEG recompression.",
        )
        findings.append(
            {
                "severity": "high",
                "title": "High ELA artifact evidence",
                "description": "ELA found strong recompression/editing indicators. High ELA may happen after editing, resaving, or platform compression.",
            }
        )
    elif artifact_risk >= 35:
        score -= 8
        add_breakdown(
            score_breakdown,
            "Compression / ELA",
            -8,
            "ELA shows moderate recompression/editing indicators after quality-90 JPEG recompression.",
        )
        findings.append(
            {
                "severity": "medium",
                "title": "Moderate ELA artifact evidence",
                "description": "ELA found moderate recompression/editing indicators. This can happen after editing, resaving, or platform compression.",
            }
        )

    noise_inconsistency = metrics.get("noiseInconsistencyScore", 100.0 - metrics["noiseConsistency"])
    if noise_inconsistency > 65:
        score -= 10
        add_breakdown(
            score_breakdown,
            "Noise consistency",
            -10,
            "Block-level noise residual variation is high, indicating inconsistent local noise patterns.",
        )
        findings.append(
            {
                "severity": "medium",
                "title": "Inconsistent noise pattern",
                "description": "Noise pattern inconsistency detected. This may indicate local editing or mixed image sources.",
            }
        )
    elif noise_inconsistency >= 40:
        score -= 5
        add_breakdown(
            score_breakdown,
            "Noise consistency",
            -5,
            "Block-level noise residual variation indicates moderate noise inconsistency.",
        )

    edge_density_score = metrics.get("edgeDensityScore", metrics["edgeDensity"])
    if edge_density_score < 5 or edge_density_score > 80:
        score -= 6
        add_breakdown(
            score_breakdown,
            "Edge density",
            -6,
            "Canny edge density score is extremely low or high compared with natural product photos.",
        )
        findings.append(
            {
                "severity": "low",
                "title": "Extreme edge density detected",
                "description": "Edge structure suggests the image may be blurry, text-heavy, screenshot-like, or overprocessed.",
            }
        )

    screenshot_probability = metrics["screenshotProbability"]
    if screenshot_probability > 70:
        score -= 20
        add_breakdown(
            score_breakdown,
            "Screenshot probability",
            -20,
            "Measured file, metadata, aspect ratio, edge, and flat-region signals indicate a likely screenshot.",
        )
        findings.append(
            {
                "severity": "high",
                "title": "Screenshot-like image structure",
                "description": "Image appears screenshot-like. Seller may be using a captured image instead of an original product photo.",
            }
        )
    elif screenshot_probability >= 40:
        score -= 10
        add_breakdown(
            score_breakdown,
            "Screenshot probability",
            -10,
            "Measured file, metadata, aspect ratio, edge, or flat-region signals indicate possible screenshot reuse.",
        )
        if screenshot_probability >= 66:
            findings.append(
                {
                    "severity": "high",
                    "title": "Screenshot-like image structure",
                    "description": "Image appears screenshot-like. Seller may be using a captured image instead of an original product photo.",
                }
            )
        else:
            findings.append(
                {
                    "severity": "medium",
                    "title": "Some screenshot-like indicators",
                    "description": "Some measurable traits resemble a screenshot, but this is not proof of fraud.",
                }
            )

    ai_like_probability = metrics.get("aiLikeProbability", 0.0)
    if ai_like_probability > 70:
        score -= 12
        add_breakdown(
            score_breakdown,
            "AI-like heuristic",
            -12,
            "Deterministic AI-like suspicion heuristic is above 70 based on screenshot, color, noise, and compression signals.",
        )
        findings.append(
            {
                "severity": "medium",
                "title": "High AI-like image signals",
                "description": "The deterministic image heuristic found high AI-like or synthetic-looking signals. This is not proof of generation.",
            }
        )
    elif ai_like_probability >= 40:
        score -= 6
        add_breakdown(
            score_breakdown,
            "AI-like heuristic",
            -6,
            "Deterministic AI-like suspicion heuristic is between 40 and 70 based on screenshot, color, noise, and compression signals.",
        )
        findings.append(
            {
                "severity": "low",
                "title": "Medium AI-like image signals",
                "description": "The deterministic image heuristic found some AI-like or synthetic-looking signals. This is not proof of generation.",
            }
        )

    if reverse_search.get("available") is True:
        matches_found = int(reverse_search.get("matchesFound") or 0)

        if matches_found >= 6:
            score -= 20
            add_breakdown(
                score_breakdown,
                "Reverse image search",
                -20,
                "Reverse image search found 6 or more similar online sources.",
            )
            findings.append(
                {
                    "severity": "high",
                    "title": "Multiple online matches found",
                    "description": "Similar images found online. Seller may be reusing internet photos or copied listing images.",
                }
            )
        elif matches_found >= 3:
            score -= 10
            add_breakdown(
                score_breakdown,
                "Reverse image search",
                -10,
                "Reverse image search found 3 or more similar online sources.",
            )
            findings.append(
                {
                    "severity": "medium",
                    "title": "Similar images found online",
                    "description": "Similar images found online. Seller may be reusing internet photos.",
                }
            )

        if reverse_search.get("stockPhotoDetected") is True:
            score -= 25
            add_breakdown(
                score_breakdown,
                "Reverse image search",
                -25,
                "A stock-photo or free-image source was detected.",
            )
            findings.append(
                {
                    "severity": "high",
                    "title": "Stock photo detected",
                    "description": "A matching source appears on a stock-photo or free-image website.",
                }
            )

        if matches_found == 0:
            score += 5
            add_breakdown(
                score_breakdown,
                "Reverse image search",
                5,
                "Reverse image search was available and found no online matches.",
            )

        if matches_found:
            recommendations.append("Compare this image with other listings because reverse search found similar sources.")
    else:
        add_breakdown(
            score_breakdown,
            "Reverse image search",
            0,
            reverse_search.get("message") or "Reverse image search was unavailable, so no score impact was applied.",
        )

    if google_vision.get("available") is True:
        product_labels = clear_product_labels(google_vision)
        brand_logos = detected_brand_logos(google_vision)
        _, ocr_character_count, ocr_word_count = google_vision_ocr_stats(google_vision)
        web_matches = int(google_vision.get("webMatches") or 0)
        watermark_detected = google_vision_signal(google_vision, "watermarkDetected")
        invoice_detected = google_vision_signal(google_vision, "invoiceLikeTextDetected")
        screenshot_text_detected = google_vision_signal(google_vision, "screenshotTextDetected")

        if product_labels:
            score += 5
            add_breakdown(
                score_breakdown,
                "Google Vision",
                5,
                f"Google Vision detected clear product labels: {', '.join(product_labels[:4])}.",
            )
            findings.append(
                {
                    "severity": "low",
                    "title": "Product labels match expected object",
                    "description": f"Google Vision detected product-like objects or labels: {', '.join(product_labels[:5])}.",
                }
            )

        if brand_logos and product_labels:
            score += 5
            add_breakdown(
                score_breakdown,
                "Google Vision",
                5,
                f"Google Vision detected branded logo(s) alongside product labels: {', '.join(brand_logos[:3])}.",
            )
            findings.append(
                {
                    "severity": "low",
                    "title": "Brand logo detected",
                    "description": f"Google Vision detected logo(s): {', '.join(brand_logos[:5])}. Verify serial number or ownership proof for branded items.",
                }
            )
            recommendations.append("Verify serial number for branded items.")

        if is_heavy_ocr_text(google_vision):
            score -= 8
            add_breakdown(
                score_breakdown,
                "Google Vision",
                -8,
                f"Google Vision detected heavy OCR text ({ocr_word_count} words, {ocr_character_count} characters), which can indicate a screenshot or listing capture.",
            )
            findings.append(
                {
                    "severity": "medium",
                    "title": "Screenshot/listing text detected",
                    "description": "Google Vision detected substantial OCR text, which can indicate a seller screenshot, listing capture, chat screenshot, or invoice image.",
                }
            )

        if screenshot_text_detected:
            findings.append(
                {
                    "severity": "medium",
                    "title": "Screenshot/listing text detected",
                    "description": "Google Vision OCR found marketplace or messaging UI keywords such as seller, chat, message, WhatsApp, rating, like, or share.",
                }
            )

        if watermark_detected:
            score -= 15
            add_breakdown(
                score_breakdown,
                "Google Vision",
                -15,
                "Google Vision OCR detected stock-photo or sample watermark text.",
            )
            findings.append(
                {
                    "severity": "high",
                    "title": "Stock watermark detected",
                    "description": "Google Vision OCR found watermark text commonly associated with stock or sample images.",
                }
            )

        if invoice_detected:
            score -= 10
            add_breakdown(
                score_breakdown,
                "Google Vision",
                -10,
                "Google Vision OCR detected invoice, receipt, payment, GST, transaction, amount, or bill-like text.",
            )
            findings.append(
                {
                    "severity": "high",
                    "title": "Invoice/payment text detected",
                    "description": "Google Vision OCR found invoice or payment-like terms. Verify the document manually before trusting it.",
                }
            )

        if web_matches >= 6:
            score -= 15
            add_breakdown(
                score_breakdown,
                "Google Vision",
                -15,
                "Google Vision web detection found 6 or more matching or visually similar web images.",
            )
            findings.append(
                {
                    "severity": "high",
                    "title": "Similar images found online",
                    "description": "Google Vision found multiple matching or visually similar images online.",
                }
            )
            recommendations.append("Avoid advance payment if image reused online.")
        elif web_matches >= 3:
            score -= 10
            add_breakdown(
                score_breakdown,
                "Google Vision",
                -10,
                "Google Vision web detection found 3 or more matching or visually similar web images.",
            )
            findings.append(
                {
                    "severity": "medium",
                    "title": "Similar images found online",
                    "description": "Google Vision found several matching or visually similar images online.",
                }
            )
            recommendations.append("Avoid advance payment if image reused online.")

        if not product_labels:
            score -= 8
            add_breakdown(
                score_breakdown,
                "Google Vision",
                -8,
                "Google Vision did not detect useful product-like labels with confidence 65 or higher.",
            )
            findings.append(
                {
                    "severity": "medium",
                    "title": "No useful object labels found",
                    "description": "Google Vision did not return clear product-like labels or localized objects for this marketplace image.",
                }
            )

        if google_vision_spoof_elevated(google_vision):
            score -= 5
            add_breakdown(
                score_breakdown,
                "Google Vision",
                -5,
                f"Google Safe Search spoof likelihood is elevated: {google_vision.get('safeSearch', {}).get('spoof')}.",
            )
    else:
        add_breakdown(
            score_breakdown,
            "Google Vision",
            0,
            google_vision.get("message") or "Google Vision was unavailable, so no score impact was applied.",
        )

    final_score = int(round(clamp(score)))
    risk_level = get_risk_level(final_score)

    if risk_level == "High Risk":
        recommendations.insert(0, "Avoid advance payment until the seller provides stronger proof of possession.")
    elif risk_level == "Medium Risk":
        recommendations.insert(0, "Request extra verification before trusting the listing.")
    else:
        recommendations.insert(0, "Continue normal marketplace safety checks before payment.")

    if not findings:
        findings.append(
            {
                "severity": "low",
                "title": "No strong suspicious indicators",
                "description": "Measured image signals do not show strong warning signs. This does not prove authenticity.",
            }
        )

    summary = build_summary(final_score, risk_level, findings, metadata, reverse_search, google_vision)
    score_adjustments = [
        f"{item['impact']:+d} {item['factor']}: {item['reason']}"
        for item in score_breakdown
    ]
    score_adjustments.append(f"Final clamped score: {final_score}.")

    return {
        "score": final_score,
        "riskLevel": risk_level,
        "summary": summary,
        "findings": findings,
        "recommendations": recommendations,
        "scoreBreakdown": score_breakdown,
        "scoreAdjustments": score_adjustments,
    }


def apply_reverse_search_to_result(
    result: dict[str, Any],
    reverse_search: dict[str, Any],
) -> dict[str, Any]:
    next_result = dict(result)
    scoring = build_professional_score(
        next_result["metadata"],
        next_result["metrics"],
        reverse_search,
        next_result.get("googleVision"),
    )
    next_result.update(scoring)
    next_result["reverseSearch"] = reverse_search
    print(
        "[analyzer] reverseSearch summary: "
        f"available={reverse_search.get('available')} "
        f"matches={reverse_search.get('matchesFound')} "
        f"stock={reverse_search.get('stockPhotoDetected')}"
    )
    google_vision = next_result.get("googleVision") or default_google_vision_result()
    print(
        "[analyzer] googleVision summary: "
        f"available={google_vision.get('available')} "
        f"webMatches={google_vision.get('webMatches')} "
        f"labels={len(google_vision.get('labels') or [])} "
        f"objects={len(google_vision.get('objects') or [])}"
    )
    print(f"[analyzer] scoreBreakdown: {scoring['scoreBreakdown']}")
    print(f"[analyzer] final score={scoring['score']} riskLevel={scoring['riskLevel']}")
    return next_result


def get_risk_level(score: int) -> str:
    if score >= 80:
        return "Low Risk"
    if score >= 60:
        return "Medium Risk"
    return "High Risk"


def build_summary(
    score: int,
    risk_level: str,
    findings: list[dict[str, str]],
    metadata: dict[str, Any],
    reverse_search: dict[str, Any] | None = None,
    google_vision: dict[str, Any] | None = None,
) -> str:
    reverse_search = reverse_search or default_reverse_search_result()
    google_vision = google_vision or default_google_vision_result()
    severe_findings = [finding for finding in findings if finding["severity"] in {"medium", "high"}]
    confidence_note = ""
    reverse_note = ""
    vision_note = ""

    if not metadata.get("exifAvailable", metadata["metadataAvailable"]):
        confidence_note = " Confidence is limited because EXIF metadata is unavailable."

    if reverse_search.get("available") and int(reverse_search.get("matchesFound") or 0) > 0:
        reverse_note = " Similar images were found online, so verify seller ownership carefully."
    elif reverse_search.get("available") and reverse_search.get("originalityScore") is not None:
        if reverse_search["originalityScore"] > 80:
            reverse_note = " No strong online reuse was detected."

    if google_vision.get("available"):
        product_labels = clear_product_labels(google_vision)
        _, ocr_character_count, ocr_word_count = google_vision_ocr_stats(google_vision)
        web_matches = int(google_vision.get("webMatches") or 0)

        if web_matches >= 3:
            vision_note = " Google Vision found similar web images, so verify that the seller owns the item."
        elif is_heavy_ocr_text(google_vision):
            vision_note = (
                f" Google Vision detected substantial text ({ocr_word_count} words, "
                f"{ocr_character_count} characters), which may indicate a captured listing or screenshot."
            )
        elif product_labels and is_low_ocr_text(google_vision):
            vision_note = " Google Vision found product-like visual labels with little OCR text."

    if risk_level == "Low Risk":
        return (
            "Image looks broadly consistent with a normal secondhand marketplace photo, "
            "with no strong manipulation indicators from the measured signals."
            + confidence_note
            + reverse_note
            + vision_note
        )

    if risk_level == "Medium Risk":
        if severe_findings:
            main_issue = severe_findings[0]["title"].lower()
            return (
                f"Image has some suspicious indicators, especially {main_issue}, "
                "but the analysis does not prove fraud."
                + confidence_note
                + reverse_note
                + vision_note
            )

        return "Image has mixed signals and should be manually verified." + confidence_note + reverse_note + vision_note

    return (
        "Image has strong suspicious indicators from measurable visual or metadata signals. "
        "Treat this as high risk, not as proof of fraud."
        + confidence_note
        + reverse_note
        + vision_note
    )


def analyze_image(path: str | Path) -> dict[str, Any]:
    image = load_image(path)
    metadata = extract_metadata(path)
    metadata_integrity, metadata_raw = calculate_metadata_integrity(metadata)
    sharpness, sharpness_raw = calculate_sharpness(image)
    local_blur_raw = calculate_local_blur_consistency(image)
    compression, compression_raw = calculate_compression_score(path)
    jpeg_block_integrity, jpeg_block_raw = calculate_jpeg_block_artifacts(image)
    copy_move_risk, copy_move_raw = calculate_copy_move_risk(image)
    noise_consistency, noise_raw = calculate_noise_consistency(image)
    edge_density, edge_raw = calculate_edge_density(image)
    screenshot_probability, screenshot_raw = calculate_screenshot_probability(image, metadata)
    color_naturalness, color_raw = calculate_color_naturalness(image)
    frequency_naturalness, frequency_raw = calculate_frequency_naturalness(image)
    metrics = {
        "metadataIntegrity": metadata_integrity,
        "sharpness": sharpness,
        "sharpnessScore": sharpness_raw["sharpnessScore"],
        "sharpnessRaw": sharpness_raw["sharpnessRaw"],
        "compression": compression,
        "elaScore": compression_raw["elaScore"],
        "elaManipulationRisk": compression_raw["elaLocalizedManipulationRisk"],
        "elaArtifactRisk": compression_raw["elaGlobalArtifactRisk"],
        "elaReliability": compression_raw["elaReliability"],
        "jpegBlockIntegrity": jpeg_block_integrity,
        "jpegBlockArtifactRisk": jpeg_block_raw["jpegBlockArtifactRisk"],
        "copyMoveRisk": copy_move_risk,
        "noiseConsistency": noise_consistency,
        "noiseInconsistencyScore": noise_raw["noiseInconsistencyScore"],
        "edgeDensity": edge_density,
        "edgeDensityScore": edge_raw["edgeDensityScore"],
        "edgeDensityPercent": edge_raw["edgeDensityPercent"],
        "screenshotProbability": screenshot_probability,
        "screenshotUiStructureScore": screenshot_raw["screenshotUiStructureScore"],
        "screenshotFileSignalScore": screenshot_raw["screenshotFileSignalScore"],
        "screenshotEdgeDensityScore": screenshot_raw["screenshotEdgeDensityScore"],
        "screenshotTextComponentScore": screenshot_raw["screenshotTextComponentScore"],
        "screenshotLowPaletteScore": screenshot_raw["screenshotLowPaletteScore"],
        "colorNaturalness": color_naturalness,
        "frequencyNaturalness": frequency_naturalness,
    }
    raw_metrics = {
        **metadata_raw,
        **sharpness_raw,
        **local_blur_raw,
        **compression_raw,
        **jpeg_block_raw,
        **copy_move_raw,
        **noise_raw,
        **edge_raw,
        **screenshot_raw,
        **color_raw,
        **frequency_raw,
    }
    ai_like_probability, ai_like_raw = calculate_ai_like_probability(metrics, raw_metrics)
    metrics["aiLikeProbability"] = ai_like_probability
    raw_metrics = {**raw_metrics, **ai_like_raw}
    reverse_search = default_reverse_search_result()
    scoring = build_professional_score(metadata, metrics, reverse_search, default_google_vision_result())

    print(f"[analyzer] metadata extracted: {metadata}")
    print(f"[analyzer] raw metric values: {raw_metrics}")
    print(f"[analyzer] normalized metrics: {metrics}")
    print(f"[analyzer] reverseSearch summary: available=False matches=0 stock=False")
    print("[analyzer] googleVision summary: available=False webMatches=0 labels=0 objects=0")
    print(f"[analyzer] scoreBreakdown: {scoring['scoreBreakdown']}")
    print(f"[analyzer] final score={scoring['score']} riskLevel={scoring['riskLevel']}")

    return {
        "score": scoring["score"],
        "riskLevel": scoring["riskLevel"],
        "summary": scoring["summary"],
        "metadata": metadata,
        "metrics": metrics,
        "ela": {
            "meanError": compression_raw["elaMeanError"],
            "maxError": compression_raw["elaMaxError"],
            "stdError": compression_raw["elaStdError"],
            "elaScore": compression_raw["elaScore"],
            "interpretation": compression_raw["elaInterpretation"],
        },
        "noise": {
            "meanNoise": noise_raw["meanNoise"],
            "noiseVariation": noise_raw["noiseVariation"],
            "noiseConsistency": noise_raw["noiseConsistency"],
            "noiseInconsistencyScore": noise_raw["noiseInconsistencyScore"],
            "interpretation": noise_raw["interpretation"],
        },
        "edge": {
            "edgeDensityPercent": edge_raw["edgeDensityPercent"],
            "edgeDensityScore": edge_raw["edgeDensityScore"],
            "sharpnessRaw": edge_raw["sharpnessRaw"],
            "sharpnessScore": edge_raw["sharpnessScore"],
            "interpretation": edge_raw["edgeInterpretation"],
        },
        "screenshot": {
            "probability": screenshot_probability,
            "flatRegionRatio": screenshot_raw["flatRegionRatio"],
            "aspectRatio": screenshot_raw["aspectRatio"],
            "formatSignal": screenshot_raw["screenshotFormatSignal"],
            "edgeSignal": screenshot_raw["screenshotEdgeSignal"],
            "interpretation": screenshot_raw["screenshotInterpretation"],
        },
        "reverseSearch": reverse_search,
        "rawMetrics": raw_metrics,
        "scoreBreakdown": scoring["scoreBreakdown"],
        "findings": scoring["findings"],
        "recommendations": scoring["recommendations"],
        "scoreAdjustments": scoring["scoreAdjustments"],
    }
