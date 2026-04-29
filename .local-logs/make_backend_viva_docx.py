from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "FraudLens_Backend_Viva_Explanation.docx"


CONTENT = [
    ("title", "FraudLens Backend Viva Explanation"),
    ("p", "Simple, pointwise notes for explaining the backend in a viva. This document is based on the current backend code in code/backend: app.py, analyzer.py, reverse_search.py, requirements.txt, uploads/, and scan_history.json."),
    ("h1", "1. Backend In One Simple Sentence"),
    ("ul", [
        "The backend is a Flask server that accepts an uploaded marketplace photo, checks the photo using image-processing techniques, optionally checks whether the same photo exists online, and returns a trust/risk report to the frontend.",
        "In layman language: the backend works like a photo inspector. It looks at the image details, hidden camera information, blur, noise, compression marks, screenshot-like signs, and online reuse signs.",
    ]),
    ("h1", "2. Backend Files And Their Role"),
    ("ul", [
        "app.py: The main Flask API file. It receives requests from the frontend, validates uploaded images, saves them temporarily, calls the analyzer, calls reverse search, and sends JSON back.",
        "analyzer.py: The main brain of the backend. It reads the image, extracts metadata, calculates image quality and fraud-related signals, calculates a final score, and prepares findings and recommendations.",
        "reverse_search.py: The optional online-check module. It uses SerpAPI Google reverse image search when an API key and a public image URL are available.",
        "requirements.txt: Lists Python packages needed by the backend.",
        "uploads/: Temporary folder where uploaded images are stored during analysis.",
        "scan_history.json: Present in the backend folder, currently empty and not used by the current app.py routes.",
        "__pycache__/: Python-created cache folder. It is not part of the project logic.",
    ]),
    ("h1", "3. Full Backend Flow"),
    ("ol", [
        "User selects an image on the frontend.",
        "Frontend sends the image to POST /api/analyze as form-data with field name image.",
        "Flask receives the file in app.py.",
        "Backend checks file size, file presence, file name, and extension.",
        "Backend saves the file in uploads/ using a random unique name.",
        "Backend calls analyze_image() from analyzer.py.",
        "analyzer.py reads the image and calculates many signals like metadata, sharpness, compression, noise, edges, colors, screenshot probability, and AI-like probability.",
        "app.py calls reverse_image_search() from reverse_search.py.",
        "If reverse search is available, online match results are added to the final score.",
        "Backend converts the result into frontend-friendly JSON.",
        "Temporary uploaded file is deleted in the finally block.",
        "Frontend receives the JSON and displays score, risk level, findings, metrics, and recommendations.",
    ]),
    ("h1", "4. app.py Explained"),
    ("h2", "4.1 Imports"),
    ("ul", [
        "os: Reads environment variables and creates folders.",
        "Path: Handles file and folder paths cleanly.",
        "uuid4: Creates a random unique filename so uploaded files do not overwrite each other.",
        "AnalysisError, analyze_image, apply_reverse_search_to_result, clamp: Imported from analyzer.py.",
        "Flask tools: Flask creates the server, jsonify sends JSON, request reads incoming upload, send_from_directory sends image files, and url_for builds URLs.",
        "CORS: Allows the frontend running on another port to call this backend.",
        "reverse_image_search: Imported from reverse_search.py for online image reuse checking.",
        "secure_filename: Makes uploaded filenames safe by removing dangerous path characters.",
    ]),
    ("h2", "4.2 Flask App And CORS"),
    ("ul", [
        "app = Flask(__name__) creates the web server application.",
        "CORS(app) allows browser requests from the frontend. Without this, the browser may block frontend-to-backend API calls.",
    ]),
    ("h2", "4.3 Backend Settings"),
    ("ul", [
        "BASE_DIR stores the backend folder path.",
        "UPLOAD_FOLDER points to code/backend/uploads.",
        "ALLOWED_EXTENSIONS limits upload types to jpg, jpeg, png, webp, bmp, tif, and tiff.",
        "MAX_UPLOAD_SIZE_BYTES is 10 MB. Larger files are rejected.",
        "os.makedirs(UPLOAD_FOLDER, exist_ok=True) creates uploads/ if it does not already exist.",
    ]),
    ("h2", "4.4 Helper Functions In app.py"),
    ("ul", [
        "allowed_file(filename): Checks whether the file has an extension and whether that extension is allowed.",
        "round_metric(value): Keeps a number between 0 and 100 using clamp(), rounds it, and converts it to an integer.",
        "frontend_payload(result): Converts detailed analyzer output into fields that the frontend expects, especially aiProb and forgery metrics.",
        "public_image_url(filename): Builds a public URL for uploaded images. Reverse search needs a public URL. If PUBLIC_BASE_URL is set, it uses that; otherwise it creates a local Flask URL.",
    ]),
    ("h2", "4.5 GET /api/health"),
    ("ul", [
        "This is a simple health-check route.",
        "It returns JSON: status is working and engine is real-image-analyzer.",
        "Viva answer: This endpoint helps us confirm that the backend server is running.",
    ]),
    ("h2", "4.6 GET /api/reverse-image/<filename>"),
    ("ul", [
        "This route serves an uploaded image from uploads/ by filename.",
        "It first sanitizes the filename using secure_filename.",
        "It rejects unsafe filenames or unsupported extensions.",
        "It is mainly useful for reverse image search because online services need an image URL.",
    ]),
    ("h2", "4.7 POST /api/analyze"),
    ("ul", [
        "This is the most important endpoint.",
        "It accepts one uploaded image.",
        "It rejects files larger than 10 MB.",
        "It rejects requests where no image is uploaded.",
        "It rejects empty filenames.",
        "It rejects unsupported file types.",
        "It creates a safe original filename and then creates a new random filename using uuid4.",
        "It saves the file temporarily into uploads/.",
        "It calls analyze_image(filepath) to calculate all image forensic results.",
        "It calls reverse_image_search(filepath, public_image_url(filename)) to check online reuse when possible.",
        "It calls apply_reverse_search_to_result() so reverse-search results can affect the final score.",
        "It calls frontend_payload() to add frontend-friendly aiProb and forgery fields.",
        "It returns the final result as JSON.",
        "If the image is invalid, it returns a 400 error.",
        "If something unexpected happens, it returns a 500 error.",
        "The finally block deletes the temporary uploaded image even if analysis fails.",
    ]),
    ("h2", "4.8 Running The Backend"),
    ("ul", [
        "The last block runs only when app.py is executed directly.",
        "It reads FLASK_DEBUG from environment variables.",
        "It reads PORT from environment variables, defaulting to 5000.",
        "So by default, the backend runs at http://127.0.0.1:5000.",
    ]),
    ("h1", "5. analyzer.py Explained"),
    ("h2", "5.1 Main Purpose"),
    ("ul", [
        "analyzer.py is the actual photo-analysis engine.",
        "It does not simply guess. It calculates measurable signals from the image.",
        "It converts these signals into a score from 0 to 100.",
        "Higher score means safer/low risk. Lower score means more suspicious/high risk.",
    ]),
    ("h2", "5.2 Important Libraries Used"),
    ("ul", [
        "Pillow (PIL): Opens images and reads metadata such as camera, date, software, GPS, format, and size.",
        "OpenCV (cv2): Performs image processing such as grayscale conversion, blur detection, edge detection, ORB feature matching, and resizing.",
        "NumPy: Performs numerical calculations on image pixels.",
        "tempfile and BytesIO: Help with temporary recompression during ELA/compression analysis.",
    ]),
    ("h2", "5.3 Constants And Error Class"),
    ("ul", [
        "NOT_AVAILABLE means a metadata value was not found.",
        "EDITING_SOFTWARE_KEYWORDS contains names like Adobe, Photoshop, Lightroom, GIMP, Canva, Snapseed, Picsart, and similar tools.",
        "AnalysisError is a custom error used when the file cannot be analyzed as an image.",
    ]),
    ("h2", "5.4 Basic Helper Functions"),
    ("ul", [
        "clamp(value): Keeps a score inside a fixed range, usually 0 to 100.",
        "normalize_range(value, low, high): Converts a raw measurement into a 0-100 score.",
        "clean_text(value): Converts values to clean strings.",
        "safe_number(value): Safely converts EXIF number formats into normal numbers.",
        "json_safe(value): Converts metadata into JSON-safe values so Flask can return it.",
        "first_text(...): Picks the first non-empty text value from many possible metadata fields.",
    ]),
    ("h2", "5.5 Metadata Reading"),
    ("ul", [
        "extract_text_metadata(): Reads normal text metadata stored in the image container.",
        "extract_xmp_metadata(): Reads XMP metadata, which can store editing or creation information.",
        "gps_coordinate_to_decimal(): Converts GPS degrees/minutes/seconds into decimal latitude/longitude.",
        "read_exif_values(): Reads normal EXIF plus nested EXIF, GPS, and Interop data.",
        "extract_metadata(): Collects camera, date, software, width, height, format, color mode, megapixels, lens, GPS, exposure details, and raw metadata.",
        "Viva explanation: Metadata is hidden information inside the photo. A real camera photo often contains camera make/model, date, exposure, lens, and sometimes GPS. Missing metadata is not proof of fraud, but it reduces confidence.",
    ]),
    ("h2", "5.6 Image Loading"),
    ("ul", [
        "load_image(path): Uses OpenCV to read the uploaded image.",
        "If OpenCV cannot read it, the backend raises AnalysisError.",
        "to_gray(image): Converts color image to grayscale because many algorithms work better on brightness values.",
    ]),
    ("h2", "5.7 Sharpness Check"),
    ("ul", [
        "calculate_sharpness(): Uses Laplacian variance.",
        "In simple words: it checks how much fine detail exists in the image.",
        "A very blurry image gets a low sharpness score.",
        "A sharp product photo gets a better score.",
        "Why useful: Blur can hide product condition or signs of editing.",
    ]),
    ("h2", "5.8 Metadata Integrity Check"),
    ("ul", [
        "calculate_metadata_integrity(): Gives points for useful metadata being present.",
        "Camera, date, lens, EXIF, color profile, GPS, and exposure details increase completeness.",
        "Editing software metadata slightly lowers the score.",
        "Why useful: Real camera photos usually have some useful capture information, while screenshots or edited images may have little or suspicious metadata.",
    ]),
    ("h2", "5.9 Local Blur Consistency"),
    ("ul", [
        "calculate_local_blur_consistency(): Divides the image into blocks and checks sharpness in each block.",
        "If one part is very sharp and another part is unusually blurred, it may indicate editing or pasted content.",
        "In layman words: it checks whether the whole photo has a natural, consistent focus pattern.",
    ]),
    ("h2", "5.10 Compression And ELA"),
    ("ul", [
        "resize_for_ela(), jpeg_recompressed_array(), estimate_jpeg_quality(), and block_means() support compression analysis.",
        "calculate_compression_score(): Performs Error Level Analysis by recompressing the image as JPEG and comparing differences.",
        "ELA means Error Level Analysis.",
        "In simple words: if a photo was edited and saved multiple times, different parts may show different compression marks.",
        "The function returns a compression score and raw ELA values like mean error, max error, and standard deviation.",
        "High ELA risk does not prove fraud. It can also happen after normal editing, resizing, or social media compression.",
    ]),
    ("h2", "5.11 JPEG Block Artifact Check"),
    ("ul", [
        "calculate_jpeg_block_artifacts(): Checks 8x8 JPEG block boundaries.",
        "JPEG images are compressed in small blocks. Strong grid-like boundary differences may indicate heavy compression or resaving.",
        "The function returns jpegBlockIntegrity and jpegBlockArtifactRisk.",
    ]),
    ("h2", "5.12 Copy-Move Risk"),
    ("ul", [
        "calculate_copy_move_risk(): Uses ORB features to find repeated visual patterns inside the same image.",
        "In simple words: it checks whether a part of the photo may have been copied and pasted elsewhere in the same photo.",
        "It looks for matching keypoints that are far apart but visually similar.",
        "This is a rough warning signal, not final proof.",
    ]),
    ("h2", "5.13 Noise Consistency"),
    ("ul", [
        "calculate_noise_consistency(): Estimates image noise after blurring and subtracting.",
        "Real photos usually have somewhat consistent sensor noise.",
        "If one region has very different noise from another, it may indicate editing, pasted content, or mixed image sources.",
        "The result includes meanNoise, noiseVariation, noiseInconsistencyScore, and interpretation.",
    ]),
    ("h2", "5.14 Edge Density"),
    ("ul", [
        "calculate_edge_density(): Uses Canny edge detection.",
        "Edges are outlines and strong changes in brightness.",
        "Very low edge density can mean the photo is blurry or low-detail.",
        "Very high edge density can mean screenshot-like, text-heavy, or overprocessed image.",
        "Balanced edge density looks more like a natural photo.",
    ]),
    ("h2", "5.15 Color Naturalness"),
    ("ul", [
        "calculate_color_naturalness(): Checks saturation, contrast, number of colors, and clipped dark/light pixels.",
        "Very oversaturated, washed out, flat, or highly clipped images are treated as less natural.",
        "This helps detect overprocessed or synthetic-looking images.",
    ]),
    ("h2", "5.16 Screenshot Probability"),
    ("ul", [
        "calculate_screenshot_probability(): Estimates whether the uploaded image looks like a screenshot.",
        "It checks aspect ratio, PNG format without metadata, missing camera metadata, many flat UI-like regions, high edge density, and software words like screenshot/snipping/Canva/Photoshop.",
        "In simple words: it asks, 'Does this look like a real camera photo or a screen capture?'",
        "Screenshots are suspicious in marketplaces because sellers may be reusing images instead of taking fresh product photos.",
    ]),
    ("h2", "5.17 Editing Software Detection"),
    ("ul", [
        "is_editing_software_detected(): Checks whether metadata mentions editing tools.",
        "has_camera_metadata(): Checks whether camera make/model is present.",
        "These helper checks are used during scoring.",
    ]),
    ("h2", "5.18 Frequency Naturalness"),
    ("ul", [
        "calculate_frequency_naturalness(): Uses Fourier transform to study texture patterns.",
        "In simple words: it checks whether the image has natural fine texture or looks too smooth/synthetic.",
        "It calculates high-frequency ratio, low-frequency ratio, entropy, and texture risk.",
    ]),
    ("h2", "5.19 AI-Like Probability"),
    ("ul", [
        "calculate_ai_like_probability(): Combines screenshot risk, color artificiality, noise irregularity, and compression artifact risk.",
        "It returns an AI-like/suspicion percentage.",
        "Important viva point: This is a heuristic, not a guaranteed AI detector.",
    ]),
    ("h2", "5.20 Reverse Search Default"),
    ("ul", [
        "default_reverse_search_result(): Gives a default result when reverse image search is not run.",
        "It marks available as False, matches as 0, and message as Reverse image search not run.",
    ]),
    ("h2", "5.21 Scoring System"),
    ("ul", [
        "build_professional_score(): Starts from a base score of 85.",
        "Camera metadata can add points.",
        "Missing camera metadata gives a small penalty because social media often removes metadata.",
        "Editing software metadata gives a bigger penalty.",
        "Very low sharpness lowers the score.",
        "High ELA/compression artifacts lower the score.",
        "Inconsistent noise lowers the score.",
        "Extreme edge density lowers the score.",
        "High screenshot probability lowers the score strongly.",
        "Unnatural color lowers the score.",
        "Reverse image search matches lower the score.",
        "Stock-photo matches lower the score strongly.",
        "No online matches with high originality can add a small bonus.",
        "The final score is clamped between 0 and 100.",
    ]),
    ("h2", "5.22 Risk Level"),
    ("ul", [
        "get_risk_level(score): Converts score into a simple label.",
        "80 to 100 means Low Risk.",
        "60 to 79 means Medium Risk.",
        "Below 60 means High Risk.",
    ]),
    ("h2", "5.23 Summary And Recommendations"),
    ("ul", [
        "build_summary(): Creates a human-readable explanation based on risk level and findings.",
        "Recommendations tell users to ask for fresh live photos, handwritten note photos, videos, or avoid advance payment in high-risk cases.",
        "Important viva point: The backend does not say fraud is proven. It gives risk indicators and safety advice.",
    ]),
    ("h2", "5.24 Final analyze_image() Function"),
    ("ul", [
        "This is the main function called by app.py.",
        "It loads the image.",
        "It extracts metadata.",
        "It calculates metadata integrity, sharpness, blur consistency, compression/ELA, JPEG blocks, copy-move risk, noise, edges, screenshot probability, color naturalness, frequency naturalness, and AI-like probability.",
        "It builds metrics and rawMetrics dictionaries.",
        "It builds the first score without reverse search.",
        "It returns JSON-ready data including score, riskLevel, summary, metadata, metrics, ELA, noise, edge, screenshot, reverseSearch, rawMetrics, scoreBreakdown, findings, recommendations, and scoreAdjustments.",
    ]),
    ("h1", "6. reverse_search.py Explained"),
    ("h2", "6.1 Main Purpose"),
    ("ul", [
        "reverse_search.py checks whether the uploaded image appears elsewhere on the internet.",
        "It uses SerpAPI's Google reverse image search endpoint.",
        "This feature is optional because it needs SERPAPI_KEY and a publicly reachable image URL.",
    ]),
    ("h2", "6.2 Important Parts"),
    ("ul", [
        "SERPAPI_ENDPOINT stores the API URL.",
        "STOCK_SITE_KEYWORDS stores popular stock/free image websites such as Shutterstock, Getty Images, iStock, Adobe, Unsplash, Pexels, Pixabay, and Alamy.",
        "MISSING_KEY_RESPONSE is returned when there is no API key.",
    ]),
    ("h2", "6.3 Environment Loading"),
    ("ul", [
        "load_local_env(): Reads simple KEY=value lines from nearby .env files.",
        "It helps load SERPAPI_KEY without adding extra dependency like python-dotenv.",
        "It does not overwrite already existing environment variables.",
    ]),
    ("h2", "6.4 Helper Functions"),
    ("ul", [
        "fallback(message): Returns a safe unavailable reverse-search response with a message.",
        "domain_from_url(url): Extracts clean domain name from a URL.",
        "is_stock_domain(domain, title, link): Checks whether a result belongs to a stock/free image website.",
        "calculate_originality_score(matches_found, stock_photo_detected): Gives a higher originality score when fewer matches are found and lowers it if stock photo is detected.",
        "parse_source(result): Converts a SerpAPI result into title, URL, and domain.",
        "parse_serpapi_results(payload): Collects image matches from SerpAPI response, removes duplicate URLs, detects stock-photo sources, counts matches, and returns a clean result.",
    ]),
    ("h2", "6.5 reverse_image_search()"),
    ("ul", [
        "This is the main reverse-search function called by app.py.",
        "It loads the local environment.",
        "If SERPAPI_KEY is missing, it skips reverse search.",
        "If image_url is missing, it skips reverse search.",
        "If image_url is localhost or 127.0.0.1, it skips reverse search because SerpAPI cannot access private local URLs.",
        "If all requirements are satisfied, it sends a GET request to SerpAPI.",
        "It handles network errors, invalid JSON, and API error messages safely.",
        "It returns whether reverse search was available, how many matches were found, source list, originality score, and whether stock photo was detected.",
    ]),
    ("h1", "7. API Endpoints In Current Backend"),
    ("ul", [
        "GET /api/health: Checks whether backend is running.",
        "GET /api/reverse-image/<filename>: Serves an uploaded image safely from uploads/.",
        "POST /api/analyze: Uploads and analyzes one image.",
    ]),
    ("h1", "8. Main Output Fields"),
    ("ul", [
        "score: Trust score from 0 to 100.",
        "riskLevel: Low Risk, Medium Risk, or High Risk.",
        "summary: Simple written explanation.",
        "metadata: Camera/date/software/size/GPS/exposure/raw metadata.",
        "metrics: Normalized numbers like sharpness, compression, noise, screenshot probability, color naturalness, and AI-like probability.",
        "rawMetrics: More detailed internal measurements used for transparency.",
        "ela: Error Level Analysis details.",
        "noise: Noise consistency details.",
        "edge: Edge density and sharpness details.",
        "screenshot: Screenshot-like indicators.",
        "reverseSearch: Online reuse result if available.",
        "scoreBreakdown: Point-by-point score changes.",
        "findings: Warnings found by backend.",
        "recommendations: Safety steps for the user.",
        "aiProb: Frontend-friendly AI-like probability.",
        "forgery: Frontend-friendly forgery metrics.",
    ]),
    ("h1", "9. Validation And Safety Features"),
    ("ul", [
        "Only selected image extensions are accepted.",
        "Maximum upload size is 10 MB.",
        "secure_filename protects against unsafe filenames.",
        "Uploaded files are renamed with uuid4 to avoid conflicts.",
        "Temporary uploaded files are deleted after analysis.",
        "Invalid image files raise AnalysisError and return a clean 400 response.",
        "Unexpected errors return a 500 response with details.",
        "Reverse image serving also validates filenames and extensions before sending files.",
    ]),
    ("h1", "10. requirements.txt Explained"),
    ("ul", [
        "flask: Creates the backend API server.",
        "flask-cors: Allows the frontend to call the backend from another port/domain.",
        "pillow: Opens images and reads metadata/EXIF.",
        "opencv-python: Performs computer vision operations like blur, edge, feature, and image-array analysis.",
        "numpy: Performs fast mathematical operations on image pixels.",
        "requests: Calls SerpAPI for reverse image search.",
    ]),
    ("h1", "11. Important Viva Points"),
    ("ul", [
        "The backend is not a court-level fraud detector. It is a risk-assessment helper.",
        "The score is based on measurable image signals, not random guessing.",
        "Missing metadata is not automatically fraud because platforms like WhatsApp, Instagram, and marketplaces often remove metadata.",
        "High compression or ELA artifacts do not always mean editing; they can also come from resaving or social media compression.",
        "Reverse image search works only with a SerpAPI key and a public image URL.",
        "Localhost images cannot be checked by SerpAPI because external services cannot access a private local server.",
        "The final result is designed to guide users to ask for proof before payment.",
    ]),
    ("h1", "12. Common Viva Questions And Answers"),
    ("h2", "Q1. What is the backend of this project?"),
    ("p", "It is a Flask-based image analysis API that receives a marketplace photo, analyzes metadata and visual forensic signals, and returns a risk score with findings and recommendations."),
    ("h2", "Q2. Why did you use Flask?"),
    ("p", "Flask is lightweight and easy to use for creating API endpoints. Our backend only needs simple routes for health check, image upload, and analysis, so Flask is suitable."),
    ("h2", "Q3. What happens when a user uploads an image?"),
    ("p", "The backend validates the image, saves it temporarily, analyzes it using analyzer.py, optionally checks reverse image search, sends JSON response to frontend, and deletes the temporary file."),
    ("h2", "Q4. What is metadata?"),
    ("p", "Metadata is hidden information inside an image, such as camera model, date, lens, software, GPS, and exposure details."),
    ("h2", "Q5. What is ELA?"),
    ("p", "ELA means Error Level Analysis. It compares the original image with a recompressed version to find unusual compression differences that may suggest editing or repeated saving."),
    ("h2", "Q6. How does the backend detect blur?"),
    ("p", "It uses Laplacian variance. A sharp image has many changes in edges and details, while a blurry image has fewer details and gets a lower score."),
    ("h2", "Q7. How does it detect screenshot-like images?"),
    ("p", "It checks signals like PNG format without metadata, missing camera data, phone-like aspect ratio, flat UI-like areas, strong edge density, and software names related to screenshots or editing."),
    ("h2", "Q8. What is noise consistency?"),
    ("p", "Noise consistency checks whether small grain/noise patterns are similar across the image. Different noise in different regions may mean editing or pasted content."),
    ("h2", "Q9. What is copy-move detection?"),
    ("p", "It checks whether a region of the same image may have been copied and pasted somewhere else by comparing visual keypoints inside the image."),
    ("h2", "Q10. How is the final score calculated?"),
    ("p", "The backend starts from a base score of 85 and adds or subtracts points based on metadata, sharpness, compression, noise, edge density, screenshot probability, color naturalness, and reverse image search results."),
    ("h2", "Q11. Does this prove fraud?"),
    ("p", "No. It gives a risk level based on measurable signals. It helps users decide whether they should ask for more proof before trusting a listing."),
    ("h2", "Q12. What are the limitations?"),
    ("p", "Normal social media compression can look suspicious, metadata can be removed by platforms, reverse search needs a public URL and API key, and image forensics can only provide warning signals, not absolute proof."),
    ("h1", "13. Short Viva Summary To Memorize"),
    ("p", "FraudLens backend is a Flask API for marketplace photo verification. The main endpoint is POST /api/analyze. It validates an uploaded image, temporarily saves it, runs analyzer.py to calculate metadata, sharpness, ELA compression, JPEG blocks, copy-move risk, noise consistency, edge density, screenshot probability, color naturalness, frequency naturalness, and AI-like probability. It optionally uses reverse_search.py through SerpAPI to find online reuse. Then it builds a final 0-100 score, risk level, findings, recommendations, and returns JSON to the frontend. The backend does not prove fraud; it gives practical risk signals to help users verify sellers before payment."),
]


def paragraph_xml(text: str, style: str | None = None, bullet: bool = False, number: bool = False) -> str:
    props = ""
    if style:
        props += f'<w:pStyle w:val="{style}"/>'
    if bullet:
        props += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
    if number:
        props += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="2"/></w:numPr>'
    return (
        "<w:p>"
        f"<w:pPr>{props}</w:pPr>"
        "<w:r>"
        f"<w:t xml:space=\"preserve\">{escape(text)}</w:t>"
        "</w:r>"
        "</w:p>"
    )


def build_document_xml() -> str:
    body: list[str] = []
    for kind, value in CONTENT:
        if kind == "title":
            body.append(paragraph_xml(str(value), "Title"))
        elif kind == "h1":
            body.append(paragraph_xml(str(value), "Heading1"))
        elif kind == "h2":
            body.append(paragraph_xml(str(value), "Heading2"))
        elif kind == "p":
            body.append(paragraph_xml(str(value)))
        elif kind == "ul":
            body.extend(paragraph_xml(item, bullet=True) for item in value)
        elif kind == "ol":
            body.extend(paragraph_xml(item, number=True) for item in value)

    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {''.join(body)}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>'''


CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
</Types>'''

RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

DOCUMENT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'''

STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="280"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="40"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="300" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="30"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="220" w:after="120"/><w:outlineLvl w:val="1"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="25"/></w:rPr>
  </w:style>
</w:styles>'''

NUMBERING = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="1">
    <w:multiLevelType w:val="singleLevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/>
      <w:numFmt w:val="bullet"/>
      <w:lvlText w:val="•"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num>
  <w:abstractNum w:abstractNumId="2">
    <w:multiLevelType w:val="singleLevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/>
      <w:numFmt w:val="decimal"/>
      <w:lvlText w:val="%1."/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="2"><w:abstractNumId w:val="2"/></w:num>
</w:numbering>'''


def main() -> None:
    with ZipFile(OUT, "w", ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", CONTENT_TYPES)
        docx.writestr("_rels/.rels", RELS)
        docx.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
        docx.writestr("word/document.xml", build_document_xml())
        docx.writestr("word/styles.xml", STYLES)
        docx.writestr("word/numbering.xml", NUMBERING)
    print(OUT)


if __name__ == "__main__":
    main()
