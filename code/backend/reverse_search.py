from __future__ import annotations

import os
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
    "message": "Reverse image search unavailable (API key missing).",
    "matchesFound": 0,
    "sources": [],
    "originalityScore": None,
    "stockPhotoDetected": False,
}


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
    return {
        "available": False,
        "message": message,
        "matchesFound": 0,
        "sources": [],
        "originalityScore": None,
        "stockPhotoDetected": False,
    }


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


def reverse_image_search(image_path: str | Path, image_url: str | None = None) -> dict[str, Any]:
    """Search the web for copies of an uploaded image through SerpAPI.

    SerpAPI's Google reverse-image endpoint requires a publicly reachable image
    URL. The local file path is accepted for logging/future extension, but the
    request cannot be performed from a private localhost-only URL.
    """
    load_local_env()
    api_key = os.getenv("SERPAPI_KEY", "").strip()

    if not api_key:
        print("[reverse_search] Reverse search skipped (no key)")
        return dict(MISSING_KEY_RESPONSE)

    if requests is None:
        print("[reverse_search] Reverse search skipped (requests package missing)")
        return fallback("Reverse image search unavailable (requests package missing).")

    if not image_url:
        print("[reverse_search] Reverse search skipped (no public image URL)")
        return fallback("Reverse image search unavailable (public image URL missing).")

    parsed_url = urlparse(image_url)

    if parsed_url.hostname in {"127.0.0.1", "localhost"}:
        print("[reverse_search] Reverse search skipped (image URL is local-only)")
        return fallback(
            "Reverse image search unavailable because the uploaded image URL is not publicly reachable."
        )

    print("[reverse_search] Reverse search started")

    try:
        response = requests.get(
            SERPAPI_ENDPOINT,
            params={
                "engine": "google_reverse_image",
                "image_url": image_url,
                "api_key": api_key,
                "hl": "en",
                "gl": "us",
                "no_cache": "false",
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
    except RequestException as exc:
        print(f"[reverse_search] Reverse search failed: {exc}")
        return fallback("Reverse image search unavailable (SerpAPI request failed).")
    except ValueError as exc:
        print(f"[reverse_search] Reverse search failed: invalid JSON: {exc}")
        return fallback("Reverse image search unavailable (invalid SerpAPI response).")

    if payload.get("error"):
        print(f"[reverse_search] Reverse search failed: {payload['error']}")
        return fallback(f"Reverse image search unavailable ({payload['error']}).")

    result = parse_serpapi_results(payload)
    print(
        "[reverse_search] Reverse search complete: "
        f"matches={result['matchesFound']} stock={result['stockPhotoDetected']}"
    )
    return result
