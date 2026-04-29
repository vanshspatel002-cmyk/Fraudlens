# FraudLens Backend API

Local Flask API for image fraud analysis, scan history, health checks, and PDF report generation.

## Base URL

```text
http://127.0.0.1:5000
```

The React dev server can call these endpoints through the Vite `/api` proxy, but direct backend examples below use the Flask URL.

## Setup

```bash
cd code/backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

The backend creates:

- `uploads/` for temporary uploaded files.
- `scan_history.json` for local scan history.

Environment variables:

- `FLASK_DEBUG=1` enables Flask debug mode.
- `LOG_LEVEL=DEBUG` changes backend log verbosity.
- `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` restricts CORS. Default is `*`.

## Error Response Format

Most JSON errors use:

```json
{
  "error": "Human-readable error message",
  "code": "machine_readable_code"
}
```

Common errors:

| Status | Code | Meaning |
| --- | --- | --- |
| `400` | `invalid_upload` | Missing file, empty filename, or unsupported extension. |
| `400` | `invalid_image` | File extension was accepted, but image analysis failed. |
| `400` | `invalid_report_payload` | PDF report JSON is missing required analysis fields. |
| `413` | `file_too_large` | Upload exceeded the configured 10 MB limit. |
| `500` | `upload_save_failed` | Backend could not save the temporary upload. |
| `500` | `history_save_failed` | Backend could not write `scan_history.json`. |
| `500` | `pdf_report_failed` | Backend could not generate the PDF. |
| `500` | `internal_server_error` | Unhandled backend error. |

## GET /api/health

Returns backend health, upload size limit, and accepted image extensions.

### Request

No body.

### Response

```json
{
  "status": "ok",
  "maxUploadMb": 10,
  "allowedExtensions": ["bmp", "jpeg", "jpg", "png", "tif", "tiff", "webp"]
}
```

### Curl

```bash
curl.exe http://127.0.0.1:5000/api/health
```

## POST /api/analyze

Uploads one image and returns the full fraud analysis result. Successful scans are also saved to `scan_history.json`.

### Request

Content type: `multipart/form-data`

Field:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `image` | file | Yes | Image file. Allowed extensions: `jpg`, `jpeg`, `png`, `webp`, `bmp`, `tif`, `tiff`. Max size: 10 MB. |

### Response

```json
{
  "score": 82.4,
  "aiProb": 18,
  "risk_level": "low",
  "explanation": "Low risk: forensic signals are broadly consistent with a natural marketplace photo.",
  "findings": [
    {
      "severity": "low",
      "title": "No major forensic warnings",
      "description": "Metadata and visual signals are broadly consistent with a normal marketplace image."
    }
  ],
  "recommendations": [
    "Risk appears low, but still verify the seller and item before payment.",
    "Use platform messaging and payment protections instead of moving off-platform."
  ],
  "image_hashes": {
    "average_hash": "ff81b9b5ad9d81ff",
    "perceptual_hash": "fac5a192874c996b",
    "difference_hash": "d42b736549312bd4"
  },
  "metadata": {
    "cameraMake": "Canon",
    "cameraModel": "EOS R50",
    "camera": "Canon EOS R50",
    "dateTaken": "2026:04:27 10:30:00",
    "date": "2026:04:27 10:30:00",
    "software": "Not detected",
    "imageWidth": 1600,
    "imageHeight": 1200,
    "imageFormat": "JPEG",
    "colorMode": "RGB",
    "gpsAvailable": false,
    "metadataCompleteness": 87.5,
    "findings": [
      "Core metadata fields are present and no editing software was detected."
    ]
  },
  "forgery": {
    "compression": 14.2,
    "elaMeanError": 2.1023,
    "elaMaxError": 31,
    "elaStdError": 4.331,
    "sharpness": 91.1,
    "edgeConsistency": 78.3,
    "edgeDensity": 73.2,
    "noiseIrregularity": 15.6,
    "noiseConsistency": 84.4,
    "compressionArtifacts": 11.5,
    "brightness": 76.2,
    "contrast": 81,
    "saturation": 69.8
  },
  "metrics": {
    "imageQuality": {
      "sharpness": 91.1,
      "brightness": 76.2,
      "contrast": 81,
      "saturation": 69.8
    },
    "forensics": {
      "compression": 14.2,
      "ela": {
        "meanError": 2.1023,
        "maxError": 31,
        "stdError": 4.331
      },
      "compressionArtifacts": 11.5,
      "noiseConsistency": 84.4,
      "noiseIrregularity": 15.6,
      "edgeConsistency": 78.3,
      "edgeDensity": 73.2
    },
    "risk": {
      "metadata": 5,
      "compressionArtifacts": 14.2,
      "sharpness": 8.9,
      "edgeDensity": 26.8,
      "noiseInconsistency": 15.6,
      "aiSuspicion": 18,
      "exposure": 21,
      "saturation": 30.2,
      "overallSuspicion": 17.6
    },
    "scoring": {
      "riskLevel": "low",
      "explanation": "Low risk: forensic signals are broadly consistent with a natural marketplace photo.",
      "weights": {
        "metadata": 0.14,
        "compression_artifacts": 0.18,
        "sharpness": 0.14,
        "noise_inconsistency": 0.17,
        "edge_density": 0.13,
        "ai_suspicion": 0.16,
        "exposure": 0.05,
        "saturation": 0.03
      }
    }
  }
}
```

Notes:

- `score` is the final trust score from `0` to `100`.
- `risk_level` is `low`, `medium`, or `high`.
- `aiProb` is the AI suspicion heuristic percentage.
- `image_hashes` are perceptual fingerprints only; the backend does not compare them with a database.

### Curl

```bash
curl.exe -X POST http://127.0.0.1:5000/api/analyze ^
  -F "image=@C:\path\to\photo.jpg"
```

## GET /api/history

Returns recent successful scans from local `scan_history.json`.

### Request

Optional query parameters:

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `limit` | integer | `50` | Number of recent scans to return. Clamped from `1` to `200`. |

### Response

```json
{
  "history": [
    {
      "timestamp": "2026-04-27T06:42:41.504000+00:00",
      "filename": "market_photo.jpg",
      "trust_score": 71.2,
      "risk_level": "low",
      "metadata_summary": {
        "camera": "Unknown",
        "date_taken": "Unknown",
        "software": "Not detected",
        "format": "JPEG",
        "dimensions": "140x120",
        "metadata_completeness": 50
      },
      "key_findings": [
        {
          "severity": "medium",
          "title": "Metadata signal",
          "description": "Camera make, model, or capture date metadata is missing."
        }
      ]
    }
  ],
  "count": 1,
  "limit": 50
}
```

### Curl

```bash
curl.exe "http://127.0.0.1:5000/api/history?limit=10"
```

## POST /api/report/pdf

Accepts an analysis result JSON object and returns a downloadable PDF report.

### Request

Content type: `application/json`

The endpoint accepts either the raw analysis result:

```json
{
  "score": 82.4,
  "risk_level": "low",
  "aiProb": 18,
  "explanation": "Low risk: forensic signals are broadly consistent with a natural marketplace photo.",
  "metadata": {
    "camera": "Canon EOS R50",
    "dateTaken": "2026:04:27 10:30:00",
    "software": "Not detected",
    "imageFormat": "JPEG",
    "imageWidth": 1600,
    "imageHeight": 1200,
    "metadataCompleteness": 87.5
  },
  "forgery": {
    "compression": 14.2,
    "sharpness": 91.1,
    "edgeConsistency": 78.3,
    "edgeDensity": 73.2,
    "noiseConsistency": 84.4,
    "noiseIrregularity": 15.6,
    "brightness": 76.2,
    "contrast": 81,
    "saturation": 69.8
  },
  "findings": [
    {
      "severity": "low",
      "title": "No major forensic warnings",
      "description": "Signals look normal."
    }
  ],
  "recommendations": [
    "Verify seller and item before payment."
  ]
}
```

Or a wrapped result:

```json
{
  "result": {
    "score": 82.4
  }
}
```

The `score` field is required.

### Response

Successful response:

```text
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename=fraudlens-report-YYYYMMDD-HHMMSS.pdf
```

The response body is binary PDF data.

### Curl

Save a PDF from an existing JSON file:

```bash
curl.exe -X POST http://127.0.0.1:5000/api/report/pdf ^
  -H "Content-Type: application/json" ^
  --data-binary "@analysis-result.json" ^
  --output fraudlens-report.pdf
```

Inline minimal example:

```bash
curl.exe -X POST http://127.0.0.1:5000/api/report/pdf ^
  -H "Content-Type: application/json" ^
  -d "{\"score\":82.4,\"risk_level\":\"low\",\"aiProb\":18,\"metadata\":{},\"forgery\":{},\"findings\":[],\"recommendations\":[]}" ^
  --output fraudlens-report.pdf
```

