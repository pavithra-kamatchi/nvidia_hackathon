import type { IncidentStatus, Urgency } from "../types";

export function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export function formatDate(date: Date): string {
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function formatCoordinate(lat: number, lon: number): string {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

export function formatIncidentType(type: string): string {
  return type
    .split("_")
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

export function hasReportedHazard(value: string | undefined): boolean {
  if (!value) return false;
  return !["", "none", "none visible", "unclear", "unknown"].includes(
    value.trim().toLowerCase(),
  );
}

export function formatAssignmentRationale(rationale: string): string {
  return rationale
    .replace(/incident_type='([^']+)'/g, (_, type: string) => `incident type ${formatIncidentType(type)}`)
    .replace(/urgency=([a-z_]+)/g, (_, urgency: string) => `urgency ${formatIncidentType(urgency)}`)
    .replace(/\[['"]?([A-Z]+)['"]?\]/g, "$1");
}

export const STATUS_LABEL: Record<IncidentStatus, string> = {
  new: "New",
  needs_review: "Needs Review",
  awaiting_approval: "Awaiting Approval",
  notified: "Notified",
  dispatched: "Dispatched",
  in_progress: "Monitoring",
  resolved: "Resolved",
  false_positive: "False Positive",
};

export const STATUS_DOT: Record<IncidentStatus, string> = {
  new: "bg-blue-500",
  needs_review: "bg-red-500",
  awaiting_approval: "bg-amber-500",
  notified: "bg-amber-500",
  dispatched: "bg-violet-500",
  in_progress: "bg-amber-500",
  resolved: "bg-emerald-500",
  false_positive: "bg-neutral-400",
};

export const STATUS_PILL: Record<IncidentStatus, string> = {
  new: "bg-blue-50 text-blue-700",
  needs_review: "bg-red-50 text-red-700",
  awaiting_approval: "bg-amber-50 text-amber-700",
  notified: "bg-amber-50 text-amber-700",
  dispatched: "bg-violet-50 text-violet-700",
  in_progress: "bg-neutral-100 text-neutral-600",
  resolved: "bg-emerald-50 text-emerald-700",
  false_positive: "bg-neutral-100 text-neutral-500",
};

export const URGENCY_LABEL: Record<Urgency, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
  unclear: "Unclear",
};

export const URGENCY_DOT: Record<Urgency, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-emerald-500",
  unclear: "bg-neutral-400",
};

export const URGENCY_TEXT: Record<Urgency, string> = {
  high: "text-red-600",
  medium: "text-amber-600",
  low: "text-emerald-600",
  unclear: "text-neutral-500",
};
