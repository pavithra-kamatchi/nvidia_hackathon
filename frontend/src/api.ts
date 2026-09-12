import { MOCK_INCIDENTS, MOCK_STATION } from "./data/mock";
import type { Incident, IncidentStatus, IngestResponse, LogEntry, Station } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  return res.json();
}

export async function fetchIncidents(): Promise<{ incidents: Incident[]; live: boolean }> {
  try {
    const incidents = await request<Incident[]>("/incidents");
    return { incidents, live: true };
  } catch {
    return { incidents: MOCK_INCIDENTS, live: false };
  }
}

export async function dispatchIncident(incidentId: string, stationIds: string[] = []): Promise<Incident | null> {
  try {
    return await request<Incident>(`/incidents/${incidentId}/dispatch`, {
      method: "POST",
      body: JSON.stringify({ station_ids: stationIds }),
    });
  } catch {
    return null;
  }
}

export async function reviewIncident(
  incidentId: string,
  approved: boolean,
  overrideUrgency?: Incident["urgency"],
  notes?: string,
): Promise<Incident | null> {
  try {
    return await request<Incident>(`/incidents/${incidentId}/review`, {
      method: "POST",
      body: JSON.stringify({ approved, override_urgency: overrideUrgency, notes }),
    });
  } catch {
    return null;
  }
}

export async function ingestImage(file: File, latitude: number, longitude: number): Promise<IngestResponse> {
  const body = new FormData();
  body.append("file", file);
  body.append("latitude", String(latitude));
  body.append("longitude", String(longitude));
  return request<IngestResponse>("/ingest", { method: "POST", body });
}

export async function fetchLogs(incidentId?: string): Promise<LogEntry[]> {
  try {
    return await request<LogEntry[]>(incidentId ? `/logs?incident_id=${encodeURIComponent(incidentId)}` : "/logs");
  } catch {
    return [];
  }
}

export async function fetchIncidentReport(incidentId: string): Promise<Record<string, unknown> | null> {
  try {
    return await request<Record<string, unknown>>(`/incidents/${incidentId}/report`);
  } catch {
    return null;
  }
}

export async function resolveIncident(incidentId: string): Promise<Incident | null> {
  try {
    return await request<Incident>(`/incidents/${incidentId}/resolve`, { method: "POST" });
  } catch {
    return null;
  }
}

export async function fetchStation(): Promise<{ station: Station; live: boolean }> {
  try {
    const stations = await request<Station[]>("/stations");
    if (stations.length === 0) throw new Error("no stations");
    return { station: stations[0], live: true };
  } catch {
    return { station: MOCK_STATION, live: false };
  }
}

export async function updateStation(
  stationId: string,
  patch: Partial<Pick<Station, "available_responders" | "available_vehicles" | "available_equipment">>,
): Promise<Station | null> {
  try {
    return await request<Station>(`/stations/${stationId}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  } catch {
    return null;
  }
}

export const ALL_STATUSES: IncidentStatus[] = [
  "new",
  "needs_review",
  "awaiting_approval",
  "notified",
  "dispatched",
  "in_progress",
  "resolved",
  "false_positive",
];
