import { useMemo } from "react";
import { Link } from "react-router-dom";
import { BarChart3, Image, ShieldAlert, TrendingUp } from "lucide-react";
import { Button } from "@/react-app/components/ui/button";
import { getAnalysisHistory } from "@/react-app/lib/analysisHistory";

const weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function formatAverage(values: number[]) {
  if (values.length === 0) return "0";
  return Math.round(values.reduce((total, value) => total + value, 0) / values.length).toString();
}

export default function Dashboard() {
  const history = useMemo(() => getAnalysisHistory(), []);
  const scores = history.map((record) => record.result.score);
  const highRiskCount = history.filter((record) => record.result.score < 40).length;
  const reportsGenerated = history.length;
  const averageScore = formatAverage(scores);

  const distribution = [
    {
      label: "Safe (70-100)",
      count: history.filter((record) => record.result.score >= 70).length,
      color: "bg-emerald-500",
    },
    {
      label: "Review (40-69)",
      count: history.filter((record) => record.result.score >= 40 && record.result.score < 70).length,
      color: "bg-yellow-500",
    },
    {
      label: "High Risk (0-39)",
      count: highRiskCount,
      color: "bg-red-500",
    },
  ];

  const weeklyActivity = weekDays.map((day, index) => ({
    day,
    count: history.filter((record) => new Date(record.createdAt).getDay() === index).length,
  }));
  const maxWeeklyCount = Math.max(...weeklyActivity.map((item) => item.count), 1);

  const detectionTypes = [
    {
      label: "Missing Metadata",
      count: history.filter((record) => record.result.metadata.camera === "Unknown").length,
    },
    {
      label: "ELA Issues",
      count: history.filter((record) => record.result.forgery.compression >= 65).length,
    },
    {
      label: "Edge Inconsistency",
      count: history.filter((record) => (record.result.forgery.edgeConsistency ?? 100) < 45).length,
    },
    {
      label: "AI-Like Signals",
      count: history.filter((record) => record.result.aiProb >= 65).length,
    },
    {
      label: "Reverse Reuse",
      count: history.filter((record) => (record.result.reverseSearch?.matchesFound ?? 0) > 0).length,
    },
  ];

  const stats = [
    {
      label: "Images Checked",
      value: history.length.toString(),
      icon: Image,
      detail: "Stored locally in this browser",
      color: "text-cyan-400",
    },
    {
      label: "High-Risk Detections",
      value: highRiskCount.toString(),
      icon: ShieldAlert,
      detail: history.length ? `${Math.round((highRiskCount / history.length) * 100)}% of scans` : "No scans yet",
      color: "text-red-400",
    },
    {
      label: "Average Trust Score",
      value: averageScore,
      icon: TrendingUp,
      detail: history.length ? "Based on completed scans" : "Run a scan to calculate",
      color: "text-emerald-400",
    },
    {
      label: "Reports Available",
      value: reportsGenerated.toString(),
      icon: BarChart3,
      detail: "One PDF per completed scan",
      color: "text-violet-400",
    },
  ];

  return (
    <div className="min-h-screen px-4 pb-12 pt-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="mb-3 text-3xl font-bold sm:text-4xl">
              <span className="gradient-text">Dashboard</span>
            </h1>
            <p className="text-muted-foreground">
              Real scan activity from this browser.
            </p>
          </div>
          <Button asChild>
            <Link to="/checker">Analyze Photo</Link>
          </Button>
        </div>

        {history.length === 0 && (
          <div className="mb-8 rounded-2xl border border-border bg-card p-6">
            <h2 className="text-lg font-semibold">No scan data yet</h2>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              The dashboard now uses real completed analyses instead of demo numbers.
              Upload an image in Photo Checker to populate these charts.
            </p>
          </div>
        )}

        <div className="mb-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-2xl border border-border bg-card p-6">
              <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-muted">
                <stat.icon className={`size-6 ${stat.color}`} />
              </div>
              <div className="mb-1 text-3xl font-bold">{stat.value}</div>
              <div className="mb-2 text-sm text-muted-foreground">{stat.label}</div>
              <div className="text-xs text-muted-foreground/70">{stat.detail}</div>
            </div>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-border bg-card p-6">
            <h3 className="mb-6 text-lg font-semibold">Trust Score Distribution</h3>
            <div className="space-y-4">
              {distribution.map((item) => {
                const percentage = history.length ? Math.round((item.count / history.length) * 100) : 0;

                return (
                  <div key={item.label}>
                    <div className="mb-2 flex justify-between text-sm">
                      <span className="text-muted-foreground">{item.label}</span>
                      <span className="font-medium">{percentage}%</span>
                    </div>
                    <div className="h-3 overflow-hidden rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full ${item.color} transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6">
            <h3 className="mb-6 text-lg font-semibold">Weekly Activity</h3>
            <div className="flex h-48 items-end justify-between px-2">
              {weeklyActivity.map((item) => (
                <div key={item.day} className="flex flex-col items-center gap-2">
                  <div
                    className="w-8 rounded-t-lg bg-gradient-to-t from-cyan-500 to-violet-500 transition-all"
                    style={{ height: `${Math.max((item.count / maxWeeklyCount) * 100, 4)}%` }}
                  />
                  <span className="text-xs text-muted-foreground">{item.day}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-border bg-card p-6">
          <h3 className="mb-6 text-lg font-semibold">Detection Types</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {detectionTypes.map((type) => {
              const percentage = history.length ? Math.round((type.count / history.length) * 100) : 0;

              return (
                <div key={type.label} className="rounded-xl bg-muted/30 p-4">
                  <div className="mb-1 text-2xl font-bold text-primary">{type.count}</div>
                  <div className="mb-3 text-sm text-muted-foreground">{type.label}</div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-violet-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
