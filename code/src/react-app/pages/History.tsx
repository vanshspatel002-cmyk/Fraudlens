import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Calendar,
  Image as ImageIcon,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { Button } from "@/react-app/components/ui/button";
import {
  clearAnalysisHistory,
  getAnalysisHistory,
  getRiskStatus,
  type AnalysisRecord,
} from "@/react-app/lib/analysisHistory";

function getScoreColor(score: number) {
  if (score >= 70) return "text-emerald-400";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
}

function StatusBadge({ score }: { score: number }) {
  const status = getRiskStatus(score);
  const config = {
    safe: {
      label: "Likely Authentic",
      icon: ShieldCheck,
      className: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
    },
    review: {
      label: "Needs Review",
      icon: TriangleAlert,
      className: "border-yellow-500/20 bg-yellow-500/10 text-yellow-400",
    },
    "high-risk": {
      label: "High Risk",
      icon: ShieldAlert,
      className: "border-red-500/20 bg-red-500/10 text-red-400",
    },
  }[status];
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-medium ${config.className}`}>
      <Icon className="size-3" />
      {config.label}
    </span>
  );
}

function formatDate(isoDate: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(isoDate));
}

function HistoryItem({ record }: { record: AnalysisRecord }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="h-24 w-24 shrink-0 overflow-hidden rounded-lg bg-muted">
          <img
            src={record.imageDataUrl}
            alt={record.fileName}
            className="h-full w-full object-cover"
          />
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-3">
            <StatusBadge score={record.result.score} />
            <span className="text-sm text-muted-foreground">
              {formatDate(record.createdAt)}
            </span>
          </div>
          <h2 className="truncate text-base font-semibold">{record.fileName}</h2>
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
            <span>
              Score{" "}
              <strong className={`text-lg ${getScoreColor(record.result.score)}`}>
                {record.result.score}
              </strong>
              /100
            </span>
            <span>AI-like signals {record.result.aiProb}%</span>
            <span>ELA risk {record.result.forgery.compression}%</span>
            <span>Reverse matches {record.result.reverseSearch?.matchesFound ?? 0}</span>
            <span>Sharpness {record.result.forgery.sharpness}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function History() {
  const initialHistory = useMemo(() => getAnalysisHistory(), []);
  const [history, setHistory] = useState(initialHistory);

  const handleClearHistory = () => {
    clearAnalysisHistory();
    setHistory([]);
  };

  return (
    <div className="min-h-screen px-4 pb-12 pt-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="mb-3 text-3xl font-bold sm:text-4xl">
              <span className="gradient-text">Scan History</span>
            </h1>
            <p className="text-muted-foreground">
              Completed analyses saved locally in this browser.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="size-4" />
              <span>{history.length} scans total</span>
            </div>
            {history.length > 0 && (
              <Button variant="outline" onClick={handleClearHistory}>
                <Trash2 className="size-4" />
                Clear
              </Button>
            )}
          </div>
        </div>

        {history.length > 0 ? (
          <div className="grid gap-4">
            {history.map((record) => (
              <HistoryItem key={record.id} record={record} />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-card px-6 py-16 text-center">
            <div className="mx-auto mb-6 flex size-20 items-center justify-center rounded-2xl bg-muted">
              <ImageIcon className="size-10 text-muted-foreground" />
            </div>
            <h2 className="mb-2 text-lg font-semibold">No scans yet</h2>
            <p className="mx-auto mb-6 max-w-md text-sm text-muted-foreground">
              Run a photo analysis to build a real history. Demo entries have been removed.
            </p>
            <Button asChild>
              <Link to="/checker">Start Scanning</Link>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
