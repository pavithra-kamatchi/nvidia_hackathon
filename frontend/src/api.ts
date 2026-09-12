import type {
  Assignment,
  Incident,
  IncidentReport,
  IngestResponse,
  LogEntry,
  Readiness,
  Station,
} from "./types";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://10.50.12.164:8081";
export const OPERATOR_ID =
  import.meta.env.VITE_OPERATOR_ID ?? "demo-controller";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 180_000);
  try {
    const response = await fetch(apiUrl(path), {
      ...init,
      headers,
      signal: init?.signal ?? controller.signal,
    });
    if (!response.ok) {
      let detail = `${init?.method ?? "GET"} ${path} failed`;
      try {
        const payload = (await response.json()) as { detail?: string };
        if (payload.detail) detail = payload.detail;
      } catch {
        // Keep the request-level message when the server has no JSON body.
      }
      throw new ApiError(detail, response.status);
    }
    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function fetchReadiness(): Promise<Readiness> {
  return request<Readiness>("/readiness");
}

export async function fetchIncidents(): Promise<Incident[]> {
  return request<Incident[]>("/incidents");
}

export async function fetchIncidentDetail(
  incidentId: string,
): Promise<Incident> {
  const report = await request<IncidentReport>(`/incidents/${incidentId}/report`);
  const detection = report.detections[0];
  const assessment = report.assessments[0];
  const assignment = report.assignments[0];
  return {
    ...report.incident,
    visible_hazards: detection?.visible_hazards,
    reasoning: assessment?.observation_and_reasoning,
    assignment,
  };
}

export async function reviewIncident(
  incidentId: string,
  approved: boolean,
  overrideUrgency?: Incident["urgency"],
  notes?: string,
): Promise<Incident> {
  return request<Incident>(`/incidents/${incidentId}/review`, {
    method: "POST",
    body: JSON.stringify({
      approved,
      operator_id: OPERATOR_ID,
      override_urgency: overrideUrgency,
      notes,
    }),
  });
}

export async function decideAllocation(
  assignmentId: string,
  approved: boolean,
  notes?: string,
): Promise<Assignment> {
  return request<Assignment>(`/allocations/${assignmentId}/decision`, {
    method: "POST",
    body: JSON.stringify({ approved, operator_id: OPERATOR_ID, notes }),
  });
}

export async function simulateNotification(
  assignmentId: string,
): Promise<{ status: "simulated"; message: string; incident: Incident }> {
  return request(`/allocations/${assignmentId}/notify`, { method: "POST" });
}

export async function ingestImage(
  file: File,
  latitude: number,
  longitude: number,
): Promise<IngestResponse> {
  const body = new FormData();
  body.append("file", file);
  body.append("latitude", String(latitude));
  body.append("longitude", String(longitude));
  return request<IngestResponse>("/ingest", { method: "POST", body });
}

export async function fetchLogs(incidentId?: string): Promise<LogEntry[]> {
  return request<LogEntry[]>(
    incidentId ? `/logs?incident_id=${encodeURIComponent(incidentId)}` : "/logs",
  );
}

export async function fetchIncidentReport(
  incidentId: string,
): Promise<IncidentReport> {
  return request<IncidentReport>(`/incidents/${incidentId}/report`);
}

export async function resolveIncident(incidentId: string): Promise<Incident> {
  return request<Incident>(`/incidents/${incidentId}/resolve`, {
    method: "POST",
  });
}

export async function fetchStations(): Promise<Station[]> {
  return request<Station[]>("/stations");
}

export async function updateStation(
  stationId: string,
  patch: Partial<
    Pick<
      Station,
      | "available_responders"
      | "available_vehicles"
      | "available_equipment"
      | "operational_status"
    >
  >,
): Promise<Station> {
  return request<Station>(`/stations/${stationId}`, {
    method: "PATCH",
    headers: { "X-Operator-ID": OPERATOR_ID },
    body: JSON.stringify(patch),
  });
}
