import { useState } from "react";
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import {
  AlertCircle,
  Activity,
  Boxes,
  Bot,
  BrainCircuit,
  CalendarDays,
  Camera,
  CheckCircle2,
  ClipboardList,
  Cpu,
  Database,
  Download,
  ExternalLink,
  FileImage,
  FileText,
  Fingerprint,
  Gauge,
  Globe2,
  type LucideIcon,
  Layers3,
  ListChecks,
  LockKeyhole,
  PackageSearch,
  Phone,
  Radar,
  RotateCcw,
  ScanSearch,
  SearchCheck,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Tags,
  TriangleAlert,
  Wrench,
} from "lucide-react";
import { Button } from "@/react-app/components/ui/button";
import { Badge } from "@/react-app/components/ui/badge";
import { saveAnalysisRecord, type AnalysisResult } from "@/react-app/lib/analysisHistory";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/react-app/components/ui/card";
import { motion } from "framer-motion";
import {
  CircularProgressbar,
  buildStyles,
} from "react-circular-progressbar";
import "react-circular-progressbar/dist/styles.css";

const steps = [
  "Checking metadata...",
  "Running forgery detection...",
  "Running Google Vision OCR...",
  "Detecting logos...",
  "Detecting objects...",
  "Checking internet presence...",
  "Calculating trust score...",
];

const MAX_UPLOAD_SIZE_MB = 10;
const ACCEPTED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"];
const PDF_SAFE_TEXT_LIMIT = 110;

const intelligenceModules = [
  { label: "EXIF", icon: Database, tone: "text-cyan-300" },
  { label: "ELA", icon: Layers3, tone: "text-violet-300" },
  { label: "Noise", icon: Fingerprint, tone: "text-emerald-300" },
  { label: "Edge", icon: Radar, tone: "text-sky-300" },
  { label: "Screenshot", icon: ScanSearch, tone: "text-red-300" },
  { label: "AI-like", icon: BrainCircuit, tone: "text-amber-300" },
  { label: "Reverse", icon: Globe2, tone: "text-cyan-200" },
  { label: "Vision", icon: SearchCheck, tone: "text-violet-200" },
];

type ResultType = AnalysisResult;

type Tone = "safe" | "warning" | "danger";

function isSupportedImage(file: File) {
  const extension = file.name.split(".").pop()?.toLowerCase();

  return (
    !!extension &&
    ACCEPTED_IMAGE_EXTENSIONS.includes(extension) &&
    (file.type === "" || file.type.startsWith("image/"))
  );
}

function asNumber(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asString(value: unknown, fallback = "Unknown") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function parseRecord(value: unknown) {
  if (!value || typeof value !== "object") return undefined;

  const output: Record<string, number | string | boolean | null> = {};

  Object.entries(value as Record<string, unknown>).forEach(([key, item]) => {
    if (
      typeof item === "number" ||
      typeof item === "string" ||
      typeof item === "boolean" ||
      item === null
    ) {
      output[key] = item;
    }
  });

  return output;
}

function parseScoredDescriptions(value: unknown) {
  return Array.isArray(value)
    ? value
        .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
        .map((item) => ({
          description: asString(item.description, ""),
          score: asNumber(item.score),
        }))
        .filter((item) => item.description)
    : [];
}

function parseVisionObjects(value: unknown) {
  return Array.isArray(value)
    ? value
        .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
        .map((item) => ({
          name: asString(item.name, ""),
          score: asNumber(item.score),
        }))
        .filter((item) => item.name)
    : [];
}

function parseStringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

function parseMatchingPages(value: unknown) {
  return Array.isArray(value)
    ? value
        .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
        .map((item) => ({
          title: asString(item.title, "Matching page"),
          url: asString(item.url, ""),
        }))
        .filter((item) => item.url)
    : [];
}

function parseStringRecord(value: unknown) {
  if (!value || typeof value !== "object") return {};

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([, item]) => typeof item === "string")
      .map(([key, item]) => [key, item as string])
  );
}

function parseBooleanRecord(value: unknown) {
  if (!value || typeof value !== "object") return {};

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([, item]) => typeof item === "boolean")
      .map(([key, item]) => [key, item as boolean])
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(bytes / 1024, 1).toFixed(1)} KB`;

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatPercent(value: number | undefined | null) {
  return typeof value === "number" && Number.isFinite(value)
    ? `${Math.round(Math.max(0, Math.min(100, value)))}%`
    : "N/A";
}

function formatNumber(value: unknown, suffix = "") {
  return typeof value === "number" && Number.isFinite(value)
    ? `${Number.isInteger(value) ? value : value.toFixed(2)}${suffix}`
    : "N/A";
}

function formatVisionScore(value: number | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "";

  const percent = value <= 1 ? value * 100 : value;
  return `${Math.round(Math.max(0, Math.min(100, percent)))}%`;
}

function previewText(value: string | undefined, limit = 260) {
  const cleaned = (value || "").replace(/\s+/g, " ").trim();

  if (!cleaned) return "";
  if (cleaned.length <= limit) return cleaned;

  return `${cleaned.slice(0, limit - 3)}...`;
}

function formatPdfText(value: string, limit = PDF_SAFE_TEXT_LIMIT) {
  const cleaned = value.replace(/\s+/g, " ").trim();

  if (cleaned.length <= limit) return cleaned;

  return `${cleaned.slice(0, limit - 3)}...`;
}

function getReportRiskLabel(score: number) {
  if (score >= 80) return "Low Risk";
  if (score >= 60) return "Medium Risk";
  return "High Risk";
}

function getReportColor(score: number): [number, number, number] {
  if (score >= 80) return [16, 185, 129];
  if (score >= 60) return [245, 158, 11];
  return [239, 68, 68];
}

function getImageFormatFromDataUrl(dataUrl: string) {
  if (dataUrl.startsWith("data:image/png")) return "PNG";
  if (dataUrl.startsWith("data:image/webp")) return "WEBP";
  return "JPEG";
}

function convertDataUrlToJpeg(dataUrl: string, maxDimension = 760) {
  return new Promise<string>((resolve, reject) => {
    const image = new Image();

    image.onload = () => {
      const scale = Math.min(1, maxDimension / Math.max(image.width, image.height));
      const width = Math.max(1, Math.round(image.width * scale));
      const height = Math.max(1, Math.round(image.height * scale));
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");

      if (!context) {
        reject(new Error("Could not prepare image preview"));
        return;
      }

      canvas.width = width;
      canvas.height = height;
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, width, height);
      context.drawImage(image, 0, 0, width, height);
      resolve(canvas.toDataURL("image/jpeg", 0.86));
    };

    image.onerror = () => reject(new Error("Could not load image preview"));
    image.src = dataUrl;
  });
}

function parseAnalysisResult(payload: unknown): ResultType {
  if (!payload || typeof payload !== "object") {
    throw new Error("Backend returned an invalid analysis response");
  }

  const raw = payload as Record<string, unknown>;
  const metadata =
    raw.metadata && typeof raw.metadata === "object"
      ? (raw.metadata as Record<string, unknown>)
      : {};
  const forgery =
    raw.forgery && typeof raw.forgery === "object"
      ? (raw.forgery as Record<string, unknown>)
      : {};
  const metrics =
    raw.metrics && typeof raw.metrics === "object"
      ? (raw.metrics as Record<string, unknown>)
      : {};
  const googleVision =
    raw.googleVision && typeof raw.googleVision === "object"
      ? (raw.googleVision as Record<string, unknown>)
      : undefined;

  const compressionRisk = asNumber(
    forgery.compression,
    100 - asNumber(metrics.compression, 100)
  );
  const noiseIrregularity = asNumber(
    forgery.noiseIrregularity,
    100 - asNumber(metrics.noiseConsistency, 100)
  );
  const edgeConsistency = asNumber(
    forgery.edgeConsistency,
    asNumber(metrics.edgeDensity)
  );
  const compressionArtifacts = asNumber(
    forgery.compressionArtifacts,
    compressionRisk
  );
  const findings = Array.isArray(raw.findings)
    ? raw.findings.filter(
        (finding): finding is {
          severity: string;
          title: string;
          description: string;
        } =>
          !!finding &&
          typeof finding === "object" &&
          typeof (finding as Record<string, unknown>).severity === "string" &&
          typeof (finding as Record<string, unknown>).title === "string" &&
          typeof (finding as Record<string, unknown>).description === "string"
      )
    : undefined;
  const recommendations = Array.isArray(raw.recommendations)
    ? raw.recommendations.filter(
        (recommendation): recommendation is string =>
          typeof recommendation === "string"
      )
    : undefined;
  const reverseSearch =
    raw.reverseSearch && typeof raw.reverseSearch === "object"
      ? (raw.reverseSearch as Record<string, unknown>)
      : undefined;
  const reverseSources = Array.isArray(reverseSearch?.sources)
    ? reverseSearch.sources
        .filter(
          (source): source is Record<string, unknown> =>
            !!source && typeof source === "object"
        )
        .map((source) => ({
          title: asString(source.title, "Untitled source"),
          url: asString(source.url, ""),
          domain: asString(source.domain, "Unknown domain"),
        }))
        .filter((source) => source.url)
    : [];
  const parsedReverseSearch = reverseSearch
    ? {
        available: reverseSearch.available === true,
        message: asString(reverseSearch.message, ""),
        matchesFound: asNumber(reverseSearch.matchesFound),
        sources: reverseSources,
        originalityScore:
          typeof reverseSearch.originalityScore === "number"
            ? reverseSearch.originalityScore
            : null,
        stockPhotoDetected: reverseSearch.stockPhotoDetected === true,
      }
    : undefined;
  const scoreAdjustments = Array.isArray(raw.scoreAdjustments)
    ? raw.scoreAdjustments.filter(
        (adjustment): adjustment is string => typeof adjustment === "string"
      )
    : undefined;
  const scoreBreakdown = Array.isArray(raw.scoreBreakdown)
    ? raw.scoreBreakdown
        .filter(
          (item): item is Record<string, unknown> =>
            !!item &&
            typeof item === "object" &&
            typeof (item as Record<string, unknown>).factor === "string" &&
            typeof (item as Record<string, unknown>).impact === "number" &&
            typeof (item as Record<string, unknown>).reason === "string"
        )
        .map((item) => ({
          factor: item.factor as string,
          impact: item.impact as number,
          reason: item.reason as string,
        }))
    : undefined;
  const parsedGoogleVision = googleVision
      ? {
        available: googleVision.available === true,
        labels: parseScoredDescriptions(googleVision.labels),
        logos: parseScoredDescriptions(googleVision.logos),
        ocrText: asString(googleVision.ocrText, ""),
        phoneNumbers: parseStringList(googleVision.phoneNumbers),
        webMatches: asNumber(googleVision.webMatches),
        matchingPages: parseMatchingPages(googleVision.matchingPages),
        objects: parseVisionObjects(googleVision.objects),
        safeSearch: parseStringRecord(googleVision.safeSearch),
        marketplaceSignals: parseBooleanRecord(googleVision.marketplaceSignals),
        message: asString(googleVision.message, ""),
      }
    : undefined;

  if (typeof raw.score !== "number" || typeof raw.aiProb !== "number") {
    throw new Error("Backend response is missing score fields");
  }

  return {
    score: asNumber(raw.score),
    riskLevel: asString(raw.riskLevel, ""),
    summary: asString(raw.summary, ""),
    aiProb: asNumber(raw.aiProb),
    metrics: parseRecord(raw.metrics),
    ela: parseRecord(raw.ela),
    noise: parseRecord(raw.noise),
    edge: parseRecord(raw.edge),
    screenshot: parseRecord(raw.screenshot),
    metadata: {
      camera: asString(metadata.camera),
      date: asString(metadata.date),
      software: asString(metadata.software, "Not detected"),
    },
    forgery: {
      compression: compressionRisk,
      sharpness: asNumber(forgery.sharpness, asNumber(metrics.sharpness)),
      edgeConsistency,
      noiseIrregularity,
      compressionArtifacts,
    },
    reverseSearch: parsedReverseSearch,
    googleVision: parsedGoogleVision,
    findings,
    recommendations,
    scoreBreakdown,
    scoreAdjustments,
  };
}

export default function PhotoChecker() {
  const [dragActive, setDragActive] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [result, setResult] = useState<ResultType | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file: File) => {
    setError(null);

    if (!isSupportedImage(file)) {
      setError(
        `Please upload a supported image file: ${ACCEPTED_IMAGE_EXTENSIONS.join(", ")}.`
      );
      return;
    }

    if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      setError(`Image is too large. Maximum size is ${MAX_UPLOAD_SIZE_MB} MB.`);
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      setSelectedImage(e.target?.result as string);
      setSelectedFile(file);
      setResult(null);
    };
    reader.onerror = () => {
      setError("Could not read this image. Try a different file.");
    };
    reader.readAsDataURL(file);
  };

  const startAnalysis = async () => {
    if (!selectedFile || !selectedImage) return;

    setLoading(true);
    setResult(null);
    setError(null);
    setStepIndex(0);

    let backendData: ResultType | null = null;

    try {
      const formData = new FormData();
      formData.append("image", selectedFile, selectedFile.name);

      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/analyze`, {
        method: "POST",
        body: formData,
      });

      const payload = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(payload?.error || "Image analysis failed");
      }

      backendData = parseAnalysisResult(payload);
    } catch (error) {
      console.error(error);
      setError(
        error instanceof Error
          ? getAnalysisErrorMessage(error)
          : "Backend not running or connection failed"
      );
      setLoading(false);
      return;
    }

    let i = 0;
    const interval = setInterval(() => {
      setStepIndex(i);
      i++;

      if (i === steps.length) {
        clearInterval(interval);

        setTimeout(() => {
          if (backendData) {
            saveAnalysisRecord({
              fileName: selectedFile.name,
              imageDataUrl: selectedImage,
              result: backendData,
            });
          }
          setResult(backendData);
          setLoading(false);
        }, 500);
      }
    }, 900);
  };

  const getColor = (score: number) => {
    if (score >= 70) return "#10b981";
    if (score >= 40) return "#f59e0b";
    return "#ef4444";
  };

  const getVerdict = (score: number) => {
    if (score >= 80) {
      return {
        label: "Likely authentic",
        detail: "Strong trust indicators",
        tone: "safe" as Tone,
        icon: ShieldCheck,
      };
    }

    if (score >= 60) {
      return {
        label: "Needs review",
        detail: "Mixed authenticity signals",
        tone: "warning" as Tone,
        icon: TriangleAlert,
      };
    }

    return {
      label: "High risk",
      detail: "Multiple suspicious signals",
      tone: "danger" as Tone,
      icon: ShieldAlert,
    };
  };

  const getToneClasses = (tone: Tone) => {
    if (tone === "safe") return "bg-emerald-500/10 text-emerald-400";
    if (tone === "warning") return "bg-amber-500/10 text-amber-400";
    return "bg-red-500/10 text-red-400";
  };

  const getBarColor = (value: number, inverted = false) => {
    const safe = inverted ? value <= 35 : value >= 70;
    const warning = inverted ? value <= 65 : value >= 40;

    if (safe) return "bg-emerald-500";
    if (warning) return "bg-amber-500";
    return "bg-red-500";
  };

  const clampPercent = (value: number) => Math.max(0, Math.min(100, value));

  const downloadPdfReport = async () => {
    if (!result) return;

    const reportVerdict = getVerdict(result.score);
    const generatedAt = new Date().toLocaleString();
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 40;
    const riskColor = getReportColor(result.score);
    const typedDoc = doc as jsPDF & { lastAutoTable?: { finalY: number } };
    const aspectRows = [
      ["Trust Score", formatPercent(result.score), "Overall safety score for the listing image."],
      ["ELA Manipulation Risk", formatPercent(result.forgery.compression), "Compression differences that may indicate editing or resaving."],
      ["Sharpness", formatPercent(result.forgery.sharpness), "How much useful detail is visible for inspection."],
      ["Edge Consistency", formatPercent(result.forgery.edgeConsistency), "Whether edge structure looks balanced for a product photo."],
      ["Noise Irregularity", formatPercent(result.forgery.noiseIrregularity), "How uneven image noise is across different regions."],
      ["Compression Artifacts", formatPercent(result.forgery.compressionArtifacts), "Global signs of heavy JPEG/platform compression."],
      ["AI-Like Signal", formatPercent(result.aiProb), "Heuristic estimate from screenshot, noise, color, and compression signs."],
    ];
    const findingsRows =
      result.findings?.map((finding) => [
        finding.severity.toUpperCase(),
        finding.title,
        finding.description,
      ]) || [["LOW", "No findings returned", "The backend did not return finding details."]];
    const recommendationsRows =
      result.recommendations?.map((recommendation, index) => [
        `${index + 1}`,
        recommendation,
      ]) || [["1", "No recommendations returned."]];
    const googleVisionRows = result.googleVision?.available
      ? [
          [
            "Labels",
            result.googleVision.labels.length
              ? result.googleVision.labels
                  .slice(0, 6)
                  .map((label) => `${label.description} ${formatVisionScore(label.score)}`)
                  .join(", ")
              : "None returned",
          ],
          [
            "Logos",
            result.googleVision.logos.length
              ? result.googleVision.logos
                  .slice(0, 6)
                  .map((logo) => `${logo.description} ${formatVisionScore(logo.score)}`)
                  .join(", ")
              : "None detected",
          ],
          ["OCR Text", formatPdfText(result.googleVision.ocrText || "No OCR text detected.", 180)],
          ["Web Matches", `${result.googleVision.webMatches}`],
          [
            "Phone Numbers",
            result.googleVision.phoneNumbers.length
              ? result.googleVision.phoneNumbers.join(", ")
              : "None detected",
          ],
          [
            "Marketplace Signals",
            Object.entries(result.googleVision.marketplaceSignals)
              .map(([key, value]) => `${key}: ${value ? "detected" : "clear"}`)
              .join("; ") || "No marketplace signals returned",
          ],
          [
            "Safe Search",
            Object.entries(result.googleVision.safeSearch)
              .map(([key, value]) => `${key}: ${value}`)
              .join("; ") || "No Safe Search values returned",
          ],
        ]
      : [["Status", result.googleVision?.message || "Google Vision unavailable"]];
    const googleVisionContributionRows =
      result.scoreBreakdown
        ?.filter((item) => item.factor === "Google Vision")
        .map((item) => [
          `${item.impact >= 0 ? "+" : ""}${item.impact}`,
          formatPdfText(item.reason, 160),
        ]) || [["0", "No Google Vision score contribution returned."]];

    const addFooter = () => {
      const pageCount = doc.getNumberOfPages();

      for (let page = 1; page <= pageCount; page += 1) {
        doc.setPage(page);
        doc.setDrawColor(226, 232, 240);
        doc.line(margin, pageHeight - 38, pageWidth - margin, pageHeight - 38);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8);
        doc.setTextColor(100, 116, 139);
        doc.text("FraudLens photo verification report", margin, pageHeight - 22);
        doc.text(`Page ${page} of ${pageCount}`, pageWidth - margin, pageHeight - 22, {
          align: "right",
        });
      }
    };

    const sectionTitle = (title: string, y: number) => {
      doc.setFont("helvetica", "bold");
      doc.setFontSize(13);
      doc.setTextColor(15, 23, 42);
      doc.text(title, margin, y);
      doc.setDrawColor(14, 165, 233);
      doc.setLineWidth(1.2);
      doc.line(margin, y + 7, margin + 96, y + 7);
    };

    const nextY = (fallback: number) => typedDoc.lastAutoTable?.finalY
      ? typedDoc.lastAutoTable.finalY + 24
      : fallback;

    doc.setFillColor(8, 47, 73);
    doc.rect(0, 0, pageWidth, 106, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(24);
    doc.setTextColor(255, 255, 255);
    doc.text("FraudLens Verification Report", margin, 48);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(186, 230, 253);
    doc.text(`Generated: ${generatedAt}`, margin, 70);
    doc.text(
      selectedFile
        ? `File: ${selectedFile.name} (${selectedFileSize})`
        : "Uploaded image report",
      margin,
      88
    );

    doc.setFillColor(...riskColor);
    doc.roundedRect(pageWidth - 174, 32, 134, 44, 7, 7, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text(getReportRiskLabel(result.score), pageWidth - 107, 50, { align: "center" });
    doc.setFontSize(9);
    doc.text(`${Math.round(result.score)} / 100 Trust Score`, pageWidth - 107, 66, {
      align: "center",
    });

    let previewY = 132;

    if (selectedImage) {
      try {
        const preview = await convertDataUrlToJpeg(selectedImage);
        doc.setDrawColor(203, 213, 225);
        doc.roundedRect(margin, previewY, 138, 108, 6, 6, "S");
        doc.addImage(preview, getImageFormatFromDataUrl(preview), margin + 8, previewY + 8, 122, 92);
      } catch {
        doc.setDrawColor(203, 213, 225);
        doc.roundedRect(margin, previewY, 138, 108, 6, 6, "S");
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9);
        doc.setTextColor(100, 116, 139);
        doc.text("Image preview unavailable", margin + 18, previewY + 58);
      }
    }

    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.setTextColor(15, 23, 42);
    doc.text("Executive Summary", margin + 158, previewY + 8);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(51, 65, 85);
    doc.text(
      doc.splitTextToSize(
        result.summary || reportVerdict.detail || "No summary returned.",
        pageWidth - margin * 2 - 158
      ),
      margin + 158,
      previewY + 30
    );
    doc.setFont("helvetica", "bold");
    doc.setTextColor(...riskColor);
    doc.text(`Verdict: ${reportVerdict.label}`, margin + 158, previewY + 84);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(71, 85, 105);
    doc.text(reportVerdict.detail, margin + 158, previewY + 100);

    sectionTitle("Aspect Percentages", 276);
    autoTable(doc, {
      startY: 292,
      head: [["Aspect", "Percentage", "Meaning"]],
      body: aspectRows,
      margin: { left: margin, right: margin },
      styles: {
        font: "helvetica",
        fontSize: 9,
        cellPadding: 7,
        textColor: [51, 65, 85],
        lineColor: [226, 232, 240],
        lineWidth: 0.5,
      },
      headStyles: {
        fillColor: [8, 47, 73],
        textColor: [255, 255, 255],
        fontStyle: "bold",
      },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: {
        0: { cellWidth: 150, fontStyle: "bold" },
        1: { cellWidth: 82, halign: "center" },
      },
    });

    const metadataY = nextY(500);
    sectionTitle("Image And Metadata", metadataY);
    autoTable(doc, {
      startY: metadataY + 16,
      head: [["Field", "Value"]],
      body: [
        ["Camera", result.metadata.camera || "Unknown"],
        ["Date Taken", result.metadata.date || "Unknown"],
        ["Software", result.metadata.software || "Unknown"],
        ["Reverse Search Status", result.reverseSearch?.available ? "Active" : "Unavailable"],
        ["Matches Found", `${result.reverseSearch?.matchesFound ?? 0}`],
        [
          "Originality Score",
          result.reverseSearch?.originalityScore == null
            ? "Unavailable"
            : `${result.reverseSearch.originalityScore} / 100`,
        ],
        ["Stock Photo Detected", result.reverseSearch?.stockPhotoDetected ? "Yes" : "No"],
      ],
      margin: { left: margin, right: margin },
      styles: { fontSize: 9, cellPadding: 7, lineColor: [226, 232, 240], lineWidth: 0.5 },
      headStyles: { fillColor: [15, 118, 110], textColor: [255, 255, 255] },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: { 0: { cellWidth: 150, fontStyle: "bold" } },
    });

    const googleVisionY = nextY(620);
    if (googleVisionY > pageHeight - 220) doc.addPage();
    const visionStartY = googleVisionY > pageHeight - 220 ? 52 : googleVisionY;
    sectionTitle("Google Vision Analysis", visionStartY);
    autoTable(doc, {
      startY: visionStartY + 16,
      head: [["Signal", "Value"]],
      body: googleVisionRows,
      margin: { left: margin, right: margin },
      styles: { fontSize: 8.5, cellPadding: 7, lineColor: [226, 232, 240], lineWidth: 0.5 },
      headStyles: { fillColor: [76, 29, 149], textColor: [255, 255, 255] },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: { 0: { cellWidth: 130, fontStyle: "bold" } },
    });

    const googleContributionY = nextY(720);
    if (googleContributionY > pageHeight - 150) doc.addPage();
    const googleContributionStartY = googleContributionY > pageHeight - 150 ? 52 : googleContributionY;
    sectionTitle("Google Vision Score Contribution", googleContributionStartY);
    autoTable(doc, {
      startY: googleContributionStartY + 16,
      head: [["Impact", "Reason"]],
      body: googleVisionContributionRows,
      margin: { left: margin, right: margin },
      styles: { fontSize: 8.5, cellPadding: 7, lineColor: [226, 232, 240], lineWidth: 0.5 },
      headStyles: { fillColor: [8, 47, 73], textColor: [255, 255, 255] },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: { 0: { cellWidth: 58, halign: "center", fontStyle: "bold" } },
    });

    doc.addPage();
    sectionTitle("Key Findings", 52);
    autoTable(doc, {
      startY: 68,
      head: [["Severity", "Finding", "Details"]],
      body: findingsRows.map(([severity, title, detail]) => [
        severity,
        formatPdfText(title, 54),
        formatPdfText(detail, 125),
      ]),
      margin: { left: margin, right: margin },
      styles: { fontSize: 8.5, cellPadding: 7, lineColor: [226, 232, 240], lineWidth: 0.5 },
      headStyles: { fillColor: [8, 47, 73], textColor: [255, 255, 255] },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: {
        0: { cellWidth: 72, fontStyle: "bold" },
        1: { cellWidth: 150, fontStyle: "bold" },
      },
    });

    const recommendationsY = nextY(280);
    sectionTitle("Recommended Actions", recommendationsY);
    autoTable(doc, {
      startY: recommendationsY + 16,
      head: [["#", "Action"]],
      body: recommendationsRows.map(([index, recommendation]) => [
        index,
        formatPdfText(recommendation, 150),
      ]),
      margin: { left: margin, right: margin },
      styles: { fontSize: 9, cellPadding: 7, lineColor: [226, 232, 240], lineWidth: 0.5 },
      headStyles: { fillColor: [15, 118, 110], textColor: [255, 255, 255] },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: { 0: { cellWidth: 42, halign: "center", fontStyle: "bold" } },
    });

    const contributionRows =
      result.scoreAdjustments?.map((adjustment) => [formatPdfText(adjustment, 165)]) || [
        ["No score contribution details returned."],
      ];
    const scoreY = nextY(500);

    if (scoreY > pageHeight - 170) {
      doc.addPage();
      sectionTitle("Trust Score Contribution", 52);
    } else {
      sectionTitle("Trust Score Contribution", scoreY);
    }

    autoTable(doc, {
      startY: scoreY > pageHeight - 170 ? 68 : scoreY + 16,
      head: [["Score Adjustment"]],
      body: contributionRows,
      margin: { left: margin, right: margin },
      styles: { fontSize: 8.5, cellPadding: 7, lineColor: [226, 232, 240], lineWidth: 0.5 },
      headStyles: { fillColor: [8, 47, 73], textColor: [255, 255, 255] },
      alternateRowStyles: { fillColor: [248, 250, 252] },
    });

    const noteY = nextY(pageHeight - 96);
    if (noteY > pageHeight - 88) doc.addPage();
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);
    doc.text("Important Note", margin, noteY > pageHeight - 88 ? 62 : noteY);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(71, 85, 105);
    doc.text(
      doc.splitTextToSize(
        "This report is a risk assessment based on measurable image signals. It does not prove fraud or authenticity. Always verify seller ownership with fresh photos, a handwritten note, or a short live video before payment.",
        pageWidth - margin * 2
      ),
      margin,
      (noteY > pageHeight - 88 ? 62 : noteY) + 18
    );

    addFooter();
    doc.save(`fraudlens-professional-report-${Date.now()}.pdf`);
  };

  const ResultMetric = ({
    icon: Icon,
    label,
    value,
    color,
  }: {
    icon: LucideIcon;
    label: string;
    value: string;
    color: string;
  }) => (
    <div className="rounded-xl border border-border bg-muted/20 p-4">
      <div className="mb-3 flex items-center gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
          <Icon className={`size-4 ${color}`} />
        </div>
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <div className="break-words text-base font-semibold">
        {value || "Unknown"}
      </div>
    </div>
  );

  const ModuleChip = ({
    icon: Icon,
    label,
    tone,
  }: {
    icon: LucideIcon;
    label: string;
    tone: string;
  }) => (
    <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-muted-foreground">
      <Icon className={`size-3.5 ${tone}`} />
      <span>{label}</span>
    </div>
  );

  const SummaryTile = ({
    icon: Icon,
    label,
    value,
    detail,
  }: {
    icon: LucideIcon;
    label: string;
    value: string;
    detail: string;
  }) => (
    <div className="rounded-lg border border-border bg-card/70 p-4 shadow-lg shadow-black/10">
      <div className="mb-3 flex items-center gap-3">
        <div className="flex size-9 items-center justify-center rounded-md bg-muted">
          <Icon className="size-4 text-cyan-300" />
        </div>
        <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
          {label}
        </span>
      </div>
      <div className="text-2xl font-semibold">{value}</div>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );

  const SignalBar = ({
    icon: Icon,
    label,
    value,
    inverted = false,
  }: {
    icon: LucideIcon;
    label: string;
    value: number;
    inverted?: boolean;
  }) => (
    <div className="rounded-xl border border-border bg-muted/20 p-4">
      <div className="mb-3 flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
            <Icon className="size-4 text-cyan-400" />
          </div>
          <span className="truncate text-sm text-muted-foreground">{label}</span>
        </div>
        <span className="shrink-0 text-sm font-semibold">{value}%</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${getBarColor(value, inverted)}`}
          style={{ width: `${clampPercent(value)}%` }}
        />
      </div>
    </div>
  );

  const ReportCard = ({
    icon: Icon,
    title,
    children,
    className = "",
  }: {
    icon: LucideIcon;
    title: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <Card className={`overflow-hidden border-white/10 bg-card/85 shadow-xl shadow-cyan-950/10 ${className}`}>
        <CardHeader className="border-b border-white/10 bg-gradient-to-r from-cyan-500/10 via-violet-500/10 to-transparent">
          <CardTitle className="flex items-center gap-2 text-base">
            <span className="flex size-9 items-center justify-center rounded-lg border border-cyan-300/20 bg-cyan-300/10">
              <Icon className="size-4 text-cyan-200" />
            </span>
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 sm:p-5">{children}</CardContent>
      </Card>
    </motion.div>
  );

  const MiniStat = ({
    label,
    value,
    tone = "text-cyan-200",
  }: {
    label: string;
    value: string | number;
    tone?: string;
  }) => (
    <div className="rounded-lg border border-white/10 bg-black/20 p-3">
      <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className={`mt-2 break-words text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  );

  const NotConfiguredCard = ({ message }: { message?: string }) => (
    <div className="rounded-lg border border-amber-300/20 bg-amber-300/10 p-4 text-sm text-amber-100">
      <div className="mb-2 flex items-center gap-2 font-medium">
        <TriangleAlert className="size-4" />
        Not configured
      </div>
      <p className="text-amber-100/80">
        {message || "This service is unavailable, so it was not used in the report."}
      </p>
    </div>
  );

  const TagList = ({
    items,
    empty,
  }: {
    items: { label: string; score?: number }[];
    empty: string;
  }) =>
    items.length > 0 ? (
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={`${item.label}-${item.score ?? "none"}`}
            className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs text-cyan-100"
          >
            {item.label}
            {typeof item.score === "number" ? ` ${formatVisionScore(item.score)}` : ""}
          </span>
        ))}
      </div>
    ) : (
      <p className="text-sm text-muted-foreground">{empty}</p>
    );

  const GoogleVisionCard = ({ googleVision }: { googleVision: ResultType["googleVision"] }) => {
    if (!googleVision?.available) {
      return (
        <ReportCard icon={SearchCheck} title="Google Vision Analysis">
          <NotConfiguredCard message={googleVision?.message} />
        </ReportCard>
      );
    }

    const ocrPreview = previewText(googleVision.ocrText);
    const safeSearchEntries = Object.entries(googleVision.safeSearch);
    const marketplaceSignalEntries = Object.entries(googleVision.marketplaceSignals);

    return (
      <ReportCard icon={SearchCheck} title="Google Vision Analysis">
        <div className="grid gap-3 sm:grid-cols-3">
          <MiniStat label="Web Matches" value={googleVision.webMatches} tone="text-violet-200" />
          <MiniStat label="Phone Numbers" value={googleVision.phoneNumbers.length} tone="text-amber-200" />
          <MiniStat label="Objects" value={googleVision.objects.length} tone="text-emerald-200" />
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <Tags className="size-4 text-cyan-300" />
              Labels
            </div>
            <TagList
              items={googleVision.labels.map((label) => ({
                label: label.description,
                score: label.score,
              }))}
              empty="No labels returned by Google Vision."
            />
          </div>

          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <Boxes className="size-4 text-violet-300" />
              Objects
            </div>
            <TagList
              items={googleVision.objects.map((object) => ({
                label: object.name,
                score: object.score,
              }))}
              empty="No localized objects returned by Google Vision."
            />
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <Sparkles className="size-4 text-amber-300" />
              Logos
            </div>
            <TagList
              items={googleVision.logos.map((logo) => ({
                label: logo.description,
                score: logo.score,
              }))}
              empty="No logos detected."
            />
          </div>

          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <FileText className="size-4 text-emerald-300" />
              OCR Text Preview
            </div>
            <p className="max-h-32 overflow-auto whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
              {ocrPreview || "No OCR text detected."}
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <Phone className="size-4 text-amber-300" />
              Phone Numbers Found
            </div>
            <TagList
              items={googleVision.phoneNumbers.map((number) => ({ label: number }))}
              empty="No phone numbers detected by OCR."
            />
          </div>

          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <ShieldCheck className="size-4 text-cyan-300" />
              Safe Search
            </div>
            {safeSearchEntries.length > 0 ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {safeSearchEntries.map(([key, value]) => (
                  <div key={key} className="rounded-md border border-white/10 bg-white/[0.03] px-3 py-2">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                      {key}
                    </p>
                    <p className="mt-1 text-sm font-medium text-cyan-100">{value}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Safe Search values were not returned.</p>
            )}
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <Globe2 className="size-4 text-violet-300" />
              Matching Pages
            </div>
            {googleVision.matchingPages.length > 0 ? (
              <div className="space-y-2">
                {googleVision.matchingPages.slice(0, 3).map((page) => (
                  <a
                    key={page.url}
                    href={page.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm transition-colors hover:border-violet-300/35 hover:bg-violet-300/10"
                  >
                    <span className="min-w-0 truncate">{page.title}</span>
                    <ExternalLink className="size-4 shrink-0 text-violet-300" />
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No matching pages returned.</p>
            )}
          </div>

          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <ListChecks className="size-4 text-emerald-300" />
              Marketplace Signals
            </div>
            {marketplaceSignalEntries.length > 0 ? (
              <div className="grid gap-2">
                {marketplaceSignalEntries.map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-3 rounded-md border border-white/10 bg-white/[0.03] px-3 py-2">
                    <span className="text-sm text-muted-foreground">{key}</span>
                    <Badge
                      variant="outline"
                      className={value ? "border-amber-300/25 bg-amber-300/10 text-amber-200" : "border-emerald-300/25 bg-emerald-300/10 text-emerald-200"}
                    >
                      {value ? "Detected" : "Clear"}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Marketplace signals were not returned.</p>
            )}
          </div>
        </div>
      </ReportCard>
    );
  };

  const ReverseSearchCard = ({
    reverseSearch,
  }: {
    reverseSearch: ResultType["reverseSearch"];
  }) => {
    const isActive = reverseSearch?.available === true;
    const originalityScore = reverseSearch?.originalityScore;
    const sources = reverseSearch?.sources?.slice(0, 3) || [];

    return (
      <Card className="border-cyan-400/20 bg-card/85 shadow-xl shadow-cyan-950/20">
        <CardHeader className="border-b border-white/10 bg-gradient-to-r from-cyan-500/10 via-violet-500/10 to-transparent">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <Globe2 className="size-5 text-cyan-300" />
              Reverse Image Search
            </CardTitle>
            <Badge
              variant="outline"
              className={`h-8 rounded-full px-3 ${
                isActive
                  ? "border-cyan-300/25 bg-cyan-300/10 text-cyan-200"
                  : "border-amber-300/25 bg-amber-300/10 text-amber-200"
              }`}
            >
              {isActive ? "Active" : "Not configured"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {!isActive && <NotConfiguredCard message={reverseSearch?.message} />}

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Matches Found
              </p>
              <p className="mt-2 text-2xl font-semibold">
                {reverseSearch?.matchesFound ?? 0}
              </p>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Originality Score
              </p>
              <p className="mt-2 text-2xl font-semibold">
                {originalityScore == null ? "N/A" : `${originalityScore}/100`}
              </p>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Stock Photo
              </p>
              <p className="mt-2 text-2xl font-semibold">
                {reverseSearch?.stockPhotoDetected ? "Yes" : "No"}
              </p>
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <p className="text-sm leading-6 text-muted-foreground">
              {reverseSearch?.message || "Reverse image search result was not returned."}
            </p>
          </div>

          {sources.length > 0 && (
            <div className="space-y-2">
              {sources.map((source) => (
                <a
                  key={source.url}
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3 text-sm transition-colors hover:border-cyan-300/35 hover:bg-cyan-300/10"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{source.title}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {source.domain}
                    </span>
                  </span>
                  <ExternalLink className="size-4 shrink-0 text-cyan-300" />
                </a>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const verdict = result ? getVerdict(result.score) : null;
  const VerdictIcon = verdict?.icon;
  const reverseSearch = result?.reverseSearch;
  const scannerProgress =
    ((Math.min(stepIndex + 1, steps.length) || 1) / steps.length) * 100;
  const selectedFileSize = selectedFile ? formatFileSize(selectedFile.size) : "";
  const reviewedSignals = result
    ? [
        result.forgery.compression,
        result.forgery.sharpness,
        result.forgery.edgeConsistency,
        result.forgery.noiseIrregularity,
        result.forgery.compressionArtifacts,
        result.aiProb,
        result.screenshot?.probability,
        result.reverseSearch ? result.reverseSearch.matchesFound : undefined,
        result.googleVision ? result.googleVision.webMatches : undefined,
      ].filter((value) => typeof value === "number").length
    : 0;

  return (
    <div className="min-h-screen px-4 pb-12 pt-24">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <section className="mb-8 overflow-hidden rounded-xl border border-white/10 bg-card/70 shadow-2xl shadow-cyan-950/20">
          <div className="grid gap-6 p-5 sm:p-7 lg:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.75fr)] lg:items-center">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1.5 text-xs font-medium text-cyan-100">
                <Sparkles className="size-3.5 text-cyan-300" />
                Forensic AI workspace
              </div>
              <h1 className="text-3xl font-semibold leading-tight sm:text-5xl">
                Photo Checker
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
                Inspect marketplace images with metadata extraction, ELA forensics,
                noise profiling, edge consistency, screenshot checks, AI-like heuristics, Reverse Image Search, and Google Vision.
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                {intelligenceModules.map((module) => (
                  <ModuleChip key={module.label} {...module} />
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Cpu className="size-4 text-violet-300" />
                  Analysis Engine
                </div>
                <Badge variant="outline" className="rounded-full border-emerald-400/20 bg-emerald-400/10 text-emerald-300">
                  Online
                </Badge>
              </div>
              <div className="space-y-3">
                {[
                  ["Signal stack", "9 modules"],
                  ["Max upload", `${MAX_UPLOAD_SIZE_MB} MB`],
                  ["Report format", "PDF"],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between border-b border-white/10 pb-3 last:border-0 last:pb-0">
                    <span className="text-sm text-muted-foreground">{label}</span>
                    <span className="text-sm font-medium">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Upload */}
        <div className="rounded-xl border border-border bg-card/80 p-4 shadow-xl shadow-black/10 sm:p-6">
          {!selectedImage ? (
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`relative overflow-hidden rounded-lg border border-dashed p-8 text-center transition-all sm:p-12 ${
                dragActive ? "border-cyan-300 bg-cyan-400/10" : "border-white/15 bg-black/10"
              }`}
            >
              <div
                className="pointer-events-none absolute inset-0 opacity-30"
                style={{
                  backgroundImage:
                    "linear-gradient(rgba(34,211,238,.18) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,.18) 1px, transparent 1px)",
                  backgroundSize: "36px 36px",
                }}
              />
              <input
                type="file"
                accept={ACCEPTED_IMAGE_EXTENSIONS.map((extension) => `.${extension}`).join(",")}
                onChange={handleFileSelect}
                className="absolute inset-0 cursor-pointer opacity-0"
              />

              <div className="relative mx-auto mb-5 flex size-16 items-center justify-center rounded-lg border border-cyan-300/20 bg-cyan-300/10">
                <FileImage className="size-8 text-cyan-300" />
              </div>
              <p className="relative text-lg font-semibold">Drop an image into the forensic queue</p>
              <p className="relative mx-auto mt-2 max-w-md text-sm text-muted-foreground">
                JPG, PNG, WEBP, BMP, or TIFF up to {MAX_UPLOAD_SIZE_MB} MB.
              </p>
              <div className="relative mt-6 flex flex-wrap justify-center gap-2">
                {intelligenceModules.map((module) => (
                  <ModuleChip key={module.label} {...module} />
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid gap-3 rounded-lg border border-white/10 bg-black/20 p-4 sm:grid-cols-3">
                <div className="flex items-center gap-3">
                  <FileImage className="size-5 text-cyan-300" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{selectedFile?.name}</p>
                    <p className="text-xs text-muted-foreground">Evidence image</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <LockKeyhole className="size-5 text-emerald-300" />
                  <div>
                    <p className="text-sm font-medium">{selectedFileSize}</p>
                    <p className="text-xs text-muted-foreground">Local preview only</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Activity className="size-5 text-violet-300" />
                  <div>
                    <p className="text-sm font-medium">
                      {loading ? "Scanning" : result ? "Report ready" : "Ready"}
                    </p>
                    <p className="text-xs text-muted-foreground">Current state</p>
                  </div>
                </div>
              </div>

              {/* Scan Area */}
              <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-muted shadow-inner shadow-black/30">
                {!loading && (
                  <img
                    src={selectedImage}
                    className="max-h-full max-w-full object-contain"
                    alt="Selected upload preview"
                  />
                )}

                {loading && (
                  <div className="relative flex h-full w-full items-center justify-center overflow-hidden bg-black">
                    <img
                      src={selectedImage}
                      className="absolute h-full w-full object-cover opacity-45 brightness-75 contrast-125 saturate-50"
                      alt=""
                    />

                    <div className="absolute inset-0 bg-cyan-950/25 mix-blend-screen" />
                    <motion.div
                      className="absolute inset-0 opacity-30"
                      style={{
                        backgroundImage:
                          "linear-gradient(rgba(34,211,238,.24) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,.24) 1px, transparent 1px)",
                        backgroundSize: "42px 42px",
                      }}
                      animate={{ backgroundPosition: ["0px 0px", "42px 42px"] }}
                      transition={{
                        duration: 7,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                    />

                    <motion.div
                      className="absolute inset-x-0 h-28 bg-gradient-to-b from-transparent via-cyan-300/35 to-transparent"
                      animate={{ y: ["-35%", "135%", "-35%"] }}
                      transition={{
                        duration: 2.6,
                        repeat: Infinity,
                        ease: "easeInOut",
                      }}
                    >
                      <div className="absolute left-0 top-1/2 h-px w-full bg-cyan-200 shadow-[0_0_22px_rgba(34,211,238,0.95)]" />
                    </motion.div>

                    <motion.div
                      className="absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-300/55"
                      animate={{ scale: [0.85, 1.2, 0.85], opacity: [0.35, 0.8, 0.35] }}
                      transition={{ duration: 2.4, repeat: Infinity }}
                    />
                    <div className="absolute left-1/2 top-1/2 h-px w-52 -translate-x-1/2 bg-cyan-200/70" />
                    <div className="absolute left-1/2 top-1/2 h-52 w-px -translate-y-1/2 bg-cyan-200/70" />

                    <div className="absolute inset-4 border border-cyan-300/35">
                      <div className="absolute -left-px -top-px h-8 w-8 border-l-2 border-t-2 border-cyan-200" />
                      <div className="absolute -right-px -top-px h-8 w-8 border-r-2 border-t-2 border-cyan-200" />
                      <div className="absolute -bottom-px -left-px h-8 w-8 border-b-2 border-l-2 border-cyan-200" />
                      <div className="absolute -bottom-px -right-px h-8 w-8 border-b-2 border-r-2 border-cyan-200" />
                    </div>

                    <motion.div
                      className="absolute left-[18%] top-[24%] h-3 w-3 rounded-full border border-amber-300 bg-amber-300/40 shadow-[0_0_18px_rgba(252,211,77,0.85)]"
                      animate={{ scale: [1, 1.6, 1], opacity: [0.6, 1, 0.6] }}
                      transition={{ duration: 1.8, repeat: Infinity }}
                    />
                    <motion.div
                      className="absolute right-[22%] top-[58%] h-3 w-3 rounded-full border border-cyan-200 bg-cyan-300/40 shadow-[0_0_18px_rgba(34,211,238,0.85)]"
                      animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                      transition={{ duration: 2.1, repeat: Infinity, delay: 0.4 }}
                    />
                    <motion.div
                      className="absolute bottom-[22%] left-[42%] h-2.5 w-2.5 rounded-full border border-red-300 bg-red-400/35 shadow-[0_0_18px_rgba(248,113,113,0.8)]"
                      animate={{ scale: [1, 1.7, 1], opacity: [0.45, 1, 0.45] }}
                      transition={{ duration: 2.2, repeat: Infinity, delay: 0.8 }}
                    />

                    <div className="absolute left-4 top-4 hidden rounded-lg border border-cyan-300/30 bg-black/55 px-3 py-2 backdrop-blur-sm sm:block">
                      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-cyan-200">
                        <Radar className="size-3.5" />
                        Forensic pass
                      </div>
                      <div className="h-1.5 w-36 overflow-hidden rounded-full bg-cyan-950">
                        <motion.div
                          className="h-full rounded-full bg-cyan-300"
                          animate={{ width: `${scannerProgress}%` }}
                          transition={{ duration: 0.35 }}
                        />
                      </div>
                    </div>

                    <div className="absolute bottom-4 left-4 right-4 rounded-xl border border-cyan-300/30 bg-black/65 p-3 text-left shadow-2xl backdrop-blur-sm sm:left-auto sm:w-80">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-sm font-semibold text-cyan-100">
                          <Fingerprint className="size-4 text-cyan-300" />
                          Scanning Image
                        </div>
                        <span className="rounded-full bg-cyan-300/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.2em] text-cyan-200">
                          Live
                        </span>
                      </div>

                      <p className="text-xs text-cyan-100/80">
                        {steps[stepIndex] || "Initializing..."}
                      </p>

                      <div className="mt-3 grid grid-cols-3 gap-1.5 sm:grid-cols-5">
                        {["META", "FORGE", "OCR", "LOGO", "OBJECT", "WEB", "SCORE"].map((signal, index) => (
                          <div
                            key={signal}
                            className={`rounded-md border px-2 py-1 text-center text-[10px] font-medium ${
                              index <= stepIndex
                                ? "border-cyan-300/45 bg-cyan-300/15 text-cyan-100"
                                : "border-white/10 bg-white/5 text-white/45"
                            }`}
                          >
                            {signal}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Buttons */}
              <div className="flex flex-col justify-center gap-3 sm:flex-row sm:gap-4">
                <Button onClick={startAnalysis} disabled={loading}>
                  <ScanSearch className="size-4" />
                  {loading ? "Analyzing..." : "Analyze Photo"}
                </Button>

                <Button
                  variant="outline"
                  disabled={loading}
                  onClick={() => {
                    setSelectedImage(null);
                    setSelectedFile(null);
                    setResult(null);
                    setError(null);
                  }}
                >
                  <RotateCcw className="size-4" />
                  Change Image
                </Button>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-500/25 bg-red-500/10 p-4 text-sm text-red-100 shadow-lg shadow-red-950/10">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-red-300" />
            <div>
              <p className="font-medium">Analysis could not be completed</p>
              <p className="mt-1 text-red-100/80">{error}</p>
            </div>
          </div>
        )}

        {/* Result */}
        {result && verdict && VerdictIcon && (
          <section className="mt-8 space-y-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-muted-foreground">
                  <Activity className="size-3.5 text-cyan-300" />
                  Case report
                </div>
                <h2 className="text-2xl font-semibold">Marketplace Image Trust Report</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Professional marketplace image analysis from metadata, forensic measurements, reverse search, and Google Vision.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Badge
                  variant="outline"
                  className={`h-8 rounded-full px-3 ${getToneClasses(verdict.tone)}`}
                >
                  <VerdictIcon className="size-3.5" />
                  {verdict.label}
                </Badge>
                <Button variant="outline" onClick={downloadPdfReport}>
                  <Download className="size-4" />
                  Download PDF Report
                </Button>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <SummaryTile
                icon={VerdictIcon}
                label="Risk Posture"
                value={verdict.label}
                detail={verdict.detail}
              />
              <SummaryTile
                icon={ScanSearch}
                label="Signals Reviewed"
                value={reviewedSignals.toString()}
                detail="Backend response fields included"
              />
              <SummaryTile
                icon={Download}
                label="Report Status"
                value="Ready"
                detail="PDF export available"
              />
            </div>

            {reverseSearch?.available && reverseSearch.matchesFound > 0 && (
              <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100 shadow-lg shadow-amber-950/10">
                Similar images found online. Seller may be reusing internet photos.
              </div>
            )}

            {reverseSearch?.available &&
              reverseSearch.matchesFound === 0 &&
              (reverseSearch.originalityScore ?? 0) > 80 && (
                <div className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 p-4 text-sm text-emerald-100 shadow-lg shadow-emerald-950/10">
                  No strong online reuse detected.
                </div>
              )}

            <div className="grid gap-5 xl:grid-cols-2">
              <ReportCard icon={VerdictIcon} title="Trust Score">
                <div className="grid gap-5 sm:grid-cols-[170px_minmax(0,1fr)] sm:items-center">
                  <div className="mx-auto w-36 sm:w-40">
                    <CircularProgressbar
                      value={result.score}
                      text={`${result.score}`}
                      styles={buildStyles({
                        textColor: "#fff",
                        textSize: "22px",
                        pathColor: getColor(result.score),
                        trailColor: "rgba(148, 163, 184, 0.18)",
                      })}
                    />
                  </div>
                  <div>
                    <Badge
                      variant="outline"
                      className={`mb-3 rounded-full px-3 ${getToneClasses(verdict.tone)}`}
                    >
                      <VerdictIcon className="size-3.5" />
                      {result.riskLevel || getReportRiskLabel(result.score)}
                    </Badge>
                    <p className="text-sm leading-6 text-muted-foreground">
                      {result.summary || verdict.detail}
                    </p>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <MiniStat label="Score Range" value="0-100" />
                      <MiniStat label="Verdict" value={verdict.label} tone={verdict.tone === "safe" ? "text-emerald-300" : verdict.tone === "warning" ? "text-amber-300" : "text-red-300"} />
                    </div>
                  </div>
                </div>
              </ReportCard>

              <ReportCard icon={Camera} title="Metadata Analysis">
                <div className="grid gap-3 sm:grid-cols-3">
                  <ResultMetric icon={Camera} label="Camera" value={result.metadata.camera} color="text-cyan-400" />
                  <ResultMetric icon={CalendarDays} label="Date" value={result.metadata.date} color="text-violet-400" />
                  <ResultMetric icon={Wrench} label="Software" value={result.metadata.software} color="text-amber-400" />
                </div>
              </ReportCard>

              <ReportCard icon={Layers3} title="ELA / Compression Analysis">
                <div className="grid gap-4 sm:grid-cols-2">
                  <SignalBar icon={PackageSearch} label="ELA Risk" value={result.forgery.compression} inverted />
                  <SignalBar icon={ShieldAlert} label="Compression Artifacts" value={result.forgery.compressionArtifacts ?? 0} inverted />
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <MiniStat label="ELA Score" value={formatNumber(result.ela?.elaScore)} />
                  <MiniStat label="Mean Error" value={formatNumber(result.ela?.meanError)} />
                  <MiniStat label="Max Error" value={formatNumber(result.ela?.maxError)} />
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  {asString(result.ela?.interpretation, "No ELA interpretation returned.")}
                </p>
              </ReportCard>

              <ReportCard icon={Fingerprint} title="Noise Analysis">
                <SignalBar icon={Fingerprint} label="Noise Irregularity" value={result.forgery.noiseIrregularity ?? 0} inverted />
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <MiniStat label="Mean Noise" value={formatNumber(result.noise?.meanNoise)} />
                  <MiniStat label="Variation" value={formatNumber(result.noise?.noiseVariation)} />
                  <MiniStat label="Consistency" value={formatPercent(asNumber(result.noise?.noiseConsistency, result.metrics?.noiseConsistency as number | undefined))} />
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  {asString(result.noise?.interpretation, "No noise interpretation returned.")}
                </p>
              </ReportCard>

              <ReportCard icon={Radar} title="Edge & Sharpness Analysis">
                <div className="grid gap-4 sm:grid-cols-2">
                  <SignalBar icon={Gauge} label="Sharpness" value={result.forgery.sharpness} />
                  <SignalBar icon={Radar} label="Edge Consistency" value={result.forgery.edgeConsistency ?? 0} />
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <MiniStat label="Edge Density" value={formatNumber(result.edge?.edgeDensityPercent, "%")} />
                  <MiniStat label="Edge Score" value={formatPercent(asNumber(result.edge?.edgeDensityScore, result.metrics?.edgeDensityScore as number | undefined))} />
                  <MiniStat label="Sharpness Raw" value={formatNumber(result.edge?.sharpnessRaw)} />
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  {asString(result.edge?.interpretation, "No edge interpretation returned.")}
                </p>
              </ReportCard>

              <ReportCard icon={ScanSearch} title="Screenshot Detection">
                <SignalBar
                  icon={ScanSearch}
                  label="Screenshot Probability"
                  value={asNumber(result.screenshot?.probability, result.metrics?.screenshotProbability as number | undefined)}
                  inverted
                />
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <MiniStat label="Flat Regions" value={formatNumber(result.screenshot?.flatRegionRatio)} />
                  <MiniStat label="Aspect Ratio" value={formatNumber(result.screenshot?.aspectRatio)} />
                  <MiniStat label="Format Signal" value={String(result.screenshot?.formatSignal ?? "N/A")} />
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  {asString(result.screenshot?.interpretation, "No screenshot interpretation returned.")}
                </p>
              </ReportCard>

              <ReportCard icon={BrainCircuit} title="AI-like Suspicion">
                <SignalBar icon={Bot} label="AI-like Visual Heuristic" value={result.aiProb} inverted />
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <MiniStat label="Heuristic" value={formatPercent(result.aiProb)} tone="text-violet-200" />
                  <MiniStat label="Signal Source" value="Backend" />
                  <MiniStat label="Scoring Use" value="Deterministic" tone="text-emerald-200" />
                </div>
              </ReportCard>

              <ReverseSearchCard reverseSearch={reverseSearch} />

              <GoogleVisionCard googleVision={result.googleVision} />

              <ReportCard icon={ClipboardList} title="Score Breakdown" className="xl:col-span-2">
                {result.scoreBreakdown && result.scoreBreakdown.length > 0 ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {result.scoreBreakdown.map((item, index) => (
                      <div key={`${item.factor}-${index}`} className="rounded-lg border border-white/10 bg-black/20 p-4">
                        <div className="mb-2 flex items-center justify-between gap-3">
                          <p className="font-medium">{item.factor}</p>
                          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.impact >= 0 ? "bg-emerald-400/10 text-emerald-300" : "bg-red-400/10 text-red-300"}`}>
                            {item.impact >= 0 ? "+" : ""}{item.impact}
                          </span>
                        </div>
                        <p className="text-sm leading-6 text-muted-foreground">{item.reason}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No score breakdown returned by the backend.</p>
                )}
              </ReportCard>

              <ReportCard icon={ListChecks} title="Findings">
                {result.findings && result.findings.length > 0 ? (
                  <div className="space-y-3">
                    {result.findings.map((finding, index) => (
                      <div key={`${finding.title}-${index}`} className="rounded-lg border border-white/10 bg-black/20 p-4">
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <Badge variant="outline" className="rounded-full border-white/10 bg-white/5 capitalize">
                            {finding.severity}
                          </Badge>
                          <p className="font-medium">{finding.title}</p>
                        </div>
                        <p className="text-sm leading-6 text-muted-foreground">{finding.description}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No findings returned by the backend.</p>
                )}
              </ReportCard>

              <ReportCard icon={CheckCircle2} title="Recommendations">
                {result.recommendations && result.recommendations.length > 0 ? (
                  <div className="space-y-3">
                    {result.recommendations.map((recommendation, index) => (
                      <div key={`${recommendation}-${index}`} className="flex gap-3 rounded-lg border border-white/10 bg-black/20 p-4">
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-cyan-300/10 text-xs font-semibold text-cyan-200">
                          {index + 1}
                        </span>
                        <p className="text-sm leading-6 text-muted-foreground">{recommendation}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No recommendations returned by the backend.</p>
                )}
              </ReportCard>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function getAnalysisErrorMessage(error: Error) {
  if (error.message === "Failed to fetch") {
    return "Could not reach the analysis backend. Start Flask or set VITE_API_URL to the backend URL.";
  }

  return error.message;
}
