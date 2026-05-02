from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests
    from requests import RequestException
except ModuleNotFoundError:
    requests = None
    RequestException = Exception


SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
SERPAPI_CONNECT_TIMEOUT_SECONDS = 10
SERPAPI_READ_TIMEOUT_SECONDS = 50
SERPAPI_MAX_ATTEMPTS = 3
STOCK_SITE_KEYWORDS = (
    "shutterstock",
    "gettyimages",
    "istockphoto",
    "adobe",
    "unsplash",
    "pexels",
    "pixabay",
    "alamy",
)
MISSING_KEY_RESPONSE = {
    "available": False,
    "message": "Reverse image search unavailable: API key missing.",
    "matchesFound": 0,
    "sources": [],
    "originalityScore": None,
    "stockPhotoDetected": False,
}
NO_RESULTS_ERROR_MARKERS = (
    "hasn't returned any results",
    "has not returned any results",
    "no results",
    "zero results",
)


def load_local_env() -> None:
    """Load simple KEY=value lines from nearby .env files without extra deps."""
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


def fallback(message: str) -> dict[str, Any]:
    reason = message.strip().rstrip(".")

    return {
        "available": False,
        "message": f"Reverse image search unavailable: {reason}.",
        "matchesFound": 0,
        "sources": [],
        "originalityScore": None,
        "stockPhotoDetected": False,
    }


def limited_result(message: str) -> dict[str, Any]:
    reason = message.strip().rstrip(".")

    return {
        "available": True,
        "limited": True,
        "message": f"Reverse image search ran with limited confidence: {reason}.",
        "matchesFound": 0,
        "sources": [],
        "originalityScore": None,
        "stockPhotoDetected": False,
    }


def safe_request_error(exc: Exception) -> str:
    message = str(exc).strip()

    if not message:
        return exc.__class__.__name__

    return message.replace("\n", " ")[:240]


def domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def is_stock_domain(domain: str, title: str = "", link: str = "") -> bool:
    haystack = f"{domain} {title} {link}".lower()
    return any(keyword in haystack for keyword in STOCK_SITE_KEYWORDS)


def calculate_originality_score(matches_found: int, stock_photo_detected: bool) -> int:
    if matches_found == 0:
        score = 100
    elif matches_found <= 2:
        score = 85
    elif matches_found <= 5:
        score = 65
    elif matches_found <= 10:
        score = 45
    else:
        score = 25

    if stock_photo_detected:
        score -= 20

    return max(0, min(100, score))


def parse_source(result: dict[str, Any]) -> dict[str, str] | None:
    link = str(result.get("link") or result.get("source") or "").strip()

    if not link:
        return None

    title = str(result.get("title") or result.get("source_name") or "Untitled source").strip()
    domain = domain_from_url(link)

    if not domain:
        return None

    return {
        "title": title,
        "url": link,
        "domain": domain,
    }


def parse_serpapi_results(payload: dict[str, Any]) -> dict[str, Any]:
    raw_results = []

    for key in ("image_results", "visual_matches", "organic_results", "inline_images"):
        value = payload.get(key)

        if isinstance(value, list):
            raw_results.extend(item for item in value if isinstance(item, dict))

    sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for result in raw_results:
        source = parse_source(result)

        if not source or source["url"] in seen_urls:
            continue

        seen_urls.add(source["url"])
        sources.append(source)

    stock_photo_detected = any(
        is_stock_domain(source["domain"], source["title"], source["url"])
        for source in sources
    )
    matches_found = len(sources)
    originality_score = calculate_originality_score(matches_found, stock_photo_detected)

    if matches_found:
        message = "Similar images found online. Seller may be reusing internet photos."
    else:
        message = "No strong online reuse detected."

    return {
        "available": True,
        "message": message,
        "matchesFound": matches_found,
        "sources": sources[:10],
        "originalityScore": originality_score,
        "stockPhotoDetected": stock_photo_detected,
    }


def is_no_results_error(message: str) -> bool:
    normalized = message.lower()
    return any(marker in normalized for marker in NO_RESULTS_ERROR_MARKERS)


def reverse_image_search(image_path: str | Path, image_url: str | None = None) -> dict[str, Any]:
    """Search the web for copies of an uploaded image through SerpAPI.

    SerpAPI's Google reverse-image endpoint requires a publicly reachable image
    URL. The local file path is accepted for logging/future extension, but the
    request cannot be performed from a private localhost-only URL.
    """
    load_local_env()
    api_key = (
        os.getenv("SERPAPI_KEY", "").strip()
        or os.getenv("SERP_API_KEY", "").strip()
        or os.getenv("SERPAPI_API_KEY", "").strip()
    )

    if not api_key:
        print("SERPAPI_KEY missing")
        return dict(MISSING_KEY_RESPONSE)

    print("SERPAPI_KEY found")

    if requests is None:
        print("[reverse_search] Reverse search skipped (requests package missing)")
        return fallback("requests package missing")

    if not image_url:
        print("[reverse_search] Reverse search skipped (no public image URL)")
        return fallback("public image URL missing")

    parsed_url = urlparse(image_url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        print(f"[reverse_search] Reverse search skipped (invalid image URL: {image_url})")
        return fallback("uploaded image URL is invalid")

    if parsed_url.hostname in {"127.0.0.1", "localhost"}:
        print("[reverse_search] Reverse search skipped (image URL is local-only)")
        return fallback("uploaded image URL is not publicly reachable")

    print("[reverse_search] Reverse search started")

    payload = None
    last_request_error = ""

    for attempt in range(1, SERPAPI_MAX_ATTEMPTS + 1):
        try:
            print(f"[reverse_search] SerpAPI attempt {attempt}/{SERPAPI_MAX_ATTEMPTS}")
            response = requests.get(
                SERPAPI_ENDPOINT,
                params={
                    "engine": "google_reverse_image",
                    "image_url": image_url,
                    "api_key": api_key,
                    "hl": "en",
                    "gl": "us",
                    "no_cache": "true" if attempt > 1 else "false",
                },
                timeout=(SERPAPI_CONNECT_TIMEOUT_SECONDS, SERPAPI_READ_TIMEOUT_SECONDS),
            )
            print(f"SerpAPI HTTP status code: {response.status_code}")

            if response.status_code >= 500 and attempt < SERPAPI_MAX_ATTEMPTS:
                time.sleep(attempt * 1.5)
                continue

            if not response.ok:
                return limited_result(f"SerpAPI returned HTTP {response.status_code}")

            payload = response.json()
            break
        except RequestException as exc:
            last_request_error = safe_request_error(exc)
            print(f"[reverse_search] SerpAPI request attempt {attempt} failed: {last_request_error}")

            if attempt < SERPAPI_MAX_ATTEMPTS:
                time.sleep(attempt * 1.5)
                continue
        except ValueError as exc:
            print(f"[reverse_search] Reverse search failed: invalid JSON: {exc}")
            return limited_result("SerpAPI returned an invalid response")

    if payload is None:
        reason = last_request_error or "request failed after retries"
        return limited_result(f"SerpAPI request failed after {SERPAPI_MAX_ATTEMPTS} attempts: {reason}")

    if payload.get("error"):
        serpapi_error = str(payload["error"])
        print(f"SerpAPI error message: {serpapi_error}")
        if is_no_results_error(serpapi_error):
            print("[reverse_search] SerpAPI returned no matches; treating as completed search")
            return parse_serpapi_results({})

        return limited_result(serpapi_error)

    result = parse_serpapi_results(payload)
    print(f"SerpAPI matches parsed: {result['matchesFound']}")
    print(
        "[reverse_search] Reverse search complete: "
        f"matches={result['matchesFound']} stock={result['stockPhotoDetected']}"
    )
    return result
