export type AnalysisResult = {
  score: number;
  riskLevel?: string;
  summary?: string;
  metadata: {
    camera: string;
    date: string;
    software: string;
  };
  forgery: {
    compression: number;
    sharpness: number;
    edgeConsistency?: number;
    noiseIrregularity?: number;
    compressionArtifacts?: number;
  };
  aiProb: number;
  reverseSearch?: {
    available: boolean;
    message: string;
    matchesFound: number;
    sources: {
      title: string;
      url: string;
      domain: string;
    }[];
    originalityScore: number | null;
    stockPhotoDetected: boolean;
  };
  googleVision?: {
    available: boolean;
    labels: {
      description: string;
      score: number;
    }[];
    logos: {
      description: string;
      score: number;
    }[];
    ocrText: string;
    phoneNumbers: string[];
    webMatches: number;
    matchingPages: {
      title: string;
      url: string;
    }[];
    objects: {
      name: string;
      score: number;
    }[];
    safeSearch: Record<string, string>;
    marketplaceSignals: Record<string, boolean>;
    message: string;
  };
  featureDiagnostics?: {
    reverseSearch?: {
      configured: boolean;
      status: string;
      message: string;
      configuredEnv?: string | null;
      missingAnyOf?: string[];
      publicBaseConfiguredEnv?: string | null;
      publicBaseLooksValid?: boolean;
    };
    googleVision?: {
      configured: boolean;
      status: string;
      message: string;
      configuredEnv?: string | null;
      missingAnyOf?: string[];
      missingSplitEnvAlternative?: string[];
    };
  };
  metrics?: Record<string, number | string | boolean | null>;
  ela?: Record<string, number | string | boolean | null>;
  noise?: Record<string, number | string | boolean | null>;
  edge?: Record<string, number | string | boolean | null>;
  screenshot?: Record<string, number | string | boolean | null>;
  findings?: {
    severity: string;
    title: string;
    description: string;
  }[];
  recommendations?: string[];
  scoreBreakdown?: {
    factor: string;
    impact: number;
    reason: string;
  }[];
  scoreAdjustments?: string[];
};

export type AnalysisRecord = {
  id: string;
  createdAt: string;
  fileName: string;
  imageDataUrl: string;
  result: AnalysisResult;
};

const STORAGE_KEY = "fraudlens.analysisHistory";
const MAX_HISTORY_ITEMS = 25;

export function getAnalysisHistory(): AnalysisRecord[] {
  try {
    if (typeof localStorage === "undefined") return [];

    const rawHistory = localStorage.getItem(STORAGE_KEY);

    if (!rawHistory) return [];

    const parsed = JSON.parse(rawHistory);
    return Array.isArray(parsed) ? parsed.filter(isAnalysisRecord) : [];
  } catch {
    return [];
  }
}

export function saveAnalysisRecord(record: Omit<AnalysisRecord, "id" | "createdAt">) {
  const nextRecord: AnalysisRecord = {
    ...record,
    id: getRecordId(),
    createdAt: new Date().toISOString(),
  };

  try {
    if (typeof localStorage === "undefined") return nextRecord;

    const nextHistory = [nextRecord, ...getAnalysisHistory()].slice(0, MAX_HISTORY_ITEMS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextHistory));
  } catch {
    return nextRecord;
  }

  return nextRecord;
}

export function clearAnalysisHistory() {
  if (typeof localStorage === "undefined") return;

  localStorage.removeItem(STORAGE_KEY);
}

export function getRiskStatus(score: number) {
  if (score >= 70) return "safe";
  if (score >= 40) return "review";
  return "high-risk";
}

function isAnalysisRecord(value: unknown): value is AnalysisRecord {
  if (!value || typeof value !== "object") return false;

  const record = value as Partial<AnalysisRecord>;
  return (
    typeof record.id === "string" &&
    typeof record.createdAt === "string" &&
    typeof record.fileName === "string" &&
    typeof record.imageDataUrl === "string" &&
    !!record.result &&
    typeof record.result.score === "number" &&
    typeof record.result.aiProb === "number"
  );
}

function getRecordId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
