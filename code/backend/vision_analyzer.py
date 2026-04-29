from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


UNAVAILABLE_MESSAGE = "Google Vision unavailable"
WATERMARK_KEYWORDS = (
    "shutterstock",
    "getty",
    "alamy",
    "adobe stock",
    "sample",
)
INVOICE_KEYWORDS = (
    "invoice",
    "bill",
    "gst",
    "paid",
    "transaction",
    "receipt",
    "amount",
)
SCREENSHOT_UI_KEYWORDS = (
    "like",
    "share",
    "seller",
    "chat",
    "message",
    "whatsapp",
    "buy now",
    "rating",
)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


def load_local_env() -> None:
    candidates = [
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]

    for env_path in candidates:
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


def unavailable_result() -> dict[str, Any]:
    return {
        "available": False,
        "message": UNAVAILABLE_MESSAGE,
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


def _credentials_available() -> bool:
    load_local_env()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip().strip('"').strip("'")

    if not credentials_path:
        print("[google_vision] Google Vision unavailable: GOOGLE_APPLICATION_CREDENTIALS is not set")
        return False

    expanded_path = Path(os.path.expandvars(credentials_path)).expanduser()

    if not expanded_path.is_file():
        print("[google_vision] Google Vision unavailable: credentials file was not found")
        return False

    return True


def _has_error(response: Any) -> bool:
    error = getattr(response, "error", None)
    return bool(getattr(error, "message", ""))


def _raise_for_response_error(response: Any, operation: str) -> None:
    if _has_error(response):
        raise RuntimeError(f"{operation} failed: {response.error.message}")


def _score_percent(value: Any) -> int:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0

    if score <= 1.0:
        score *= 100.0

    return int(round(max(0.0, min(100.0, score))))


def _scored_annotations(annotations: Any) -> list[dict[str, Any]]:
    return [
        {
            "description": annotation.description,
            "score": _score_percent(annotation.score),
        }
        for annotation in annotations
    ]


def _localized_objects(objects: Any) -> list[dict[str, Any]]:
    return [
        {
            "name": localized_object.name,
            "score": _score_percent(localized_object.score),
        }
        for localized_object in objects
    ]


def _matching_pages(web_detection: Any) -> list[dict[str, str]]:
    pages = []

    for page in getattr(web_detection, "pages_with_matching_images", []) or []:
        url = str(getattr(page, "url", "") or "").strip()

        if not url:
            continue

        title = str(getattr(page, "page_title", "") or getattr(page, "title", "") or url).strip()
        pages.append({"title": title, "url": url})

    return pages[:10]


def _web_matches(web_detection: Any) -> int:
    return sum(
        len(getattr(web_detection, field, []) or [])
        for field in (
            "pages_with_matching_images",
            "full_matching_images",
            "partial_matching_images",
            "visually_similar_images",
        )
    )


def _extract_phone_numbers(text: str) -> list[str]:
    phone_numbers: list[str] = []
    seen: set[str] = set()

    for match in PHONE_PATTERN.findall(text):
        cleaned = re.sub(r"[^\d+]", "", match)
        digits = re.sub(r"\D", "", cleaned)

        if len(digits) < 8 or len(digits) > 15 or cleaned in seen:
            continue

        seen.add(cleaned)
        phone_numbers.append(cleaned)

    return phone_numbers


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in keywords)


def _marketplace_signals(ocr_text: str, logos: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "screenshotTextDetected": _contains_keyword(ocr_text, SCREENSHOT_UI_KEYWORDS),
        "watermarkDetected": _contains_keyword(ocr_text, WATERMARK_KEYWORDS),
        "invoiceLikeTextDetected": _contains_keyword(ocr_text, INVOICE_KEYWORDS),
        "brandLogoDetected": bool(logos),
    }


def _likelihood_name(vision: Any, value: Any) -> str:
    try:
        return vision.Likelihood(value).name
    except (TypeError, ValueError, AttributeError):
        return str(value)


def _safe_search(vision: Any, annotation: Any) -> dict[str, str]:
    if not annotation:
        return {}

    return {
        "adult": _likelihood_name(vision, getattr(annotation, "adult", "")),
        "spoof": _likelihood_name(vision, getattr(annotation, "spoof", "")),
        "medical": _likelihood_name(vision, getattr(annotation, "medical", "")),
        "violence": _likelihood_name(vision, getattr(annotation, "violence", "")),
    }


def analyze_google_vision(image_path: str | Path) -> dict[str, Any]:
    print("[google_vision] Google Vision started")

    if not _credentials_available():
        return unavailable_result()

    try:
        from google.cloud import vision

        client = vision.ImageAnnotatorClient()

        with open(image_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)

        label_response = client.label_detection(image=image)
        logo_response = client.logo_detection(image=image)
        text_response = client.text_detection(image=image)
        web_response = client.web_detection(image=image)
        safe_search_response = client.safe_search_detection(image=image)
        object_response = client.object_localization(image=image)

        for operation, response in (
            ("label_detection", label_response),
            ("logo_detection", logo_response),
            ("text_detection", text_response),
            ("web_detection", web_response),
            ("safe_search_detection", safe_search_response),
            ("object_localization", object_response),
        ):
            _raise_for_response_error(response, operation)

        text_annotations = list(text_response.text_annotations or [])
        ocr_text = text_annotations[0].description if text_annotations else ""
        labels = _scored_annotations(label_response.label_annotations or [])
        logos = _scored_annotations(logo_response.logo_annotations or [])
        web_detection = web_response.web_detection
        result = {
            "available": True,
            "message": "Google Vision completed",
            "labels": labels,
            "logos": logos,
            "ocrText": ocr_text,
            "phoneNumbers": _extract_phone_numbers(ocr_text),
            "webMatches": _web_matches(web_detection),
            "matchingPages": _matching_pages(web_detection),
            "objects": _localized_objects(object_response.localized_object_annotations or []),
            "safeSearch": _safe_search(vision, safe_search_response.safe_search_annotation),
            "marketplaceSignals": _marketplace_signals(ocr_text, logos),
        }
        print(
            "[google_vision] Google Vision completed: "
            f"labels={len(result['labels'])} logos={len(result['logos'])} "
            f"objects={len(result['objects'])} webMatches={result['webMatches']} "
            f"phones={len(result['phoneNumbers'])}"
        )
        return result
    except Exception as exc:
        print(f"[google_vision] Google Vision unavailable: {exc}")
        return unavailable_result()
