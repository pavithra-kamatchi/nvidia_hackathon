export type Urgency = "high" | "medium" | "low" | "unclear";

export type IncidentStatus =
  | "new"
  | "needs_review"
  | "awaiting_approval"
  | "notified"
  | "dispatched"
  | "in_progress"
  | "resolved"
  | "false_positive";

export type PoseLabel = "lying" | "sitting" | "bent" | "kneeling" | "upright";

export interface Coordinate {
  latitude: number;
  longitude: number;
}

export interface Station {
  station_id: string;
  name: string;
  location: Coordinate;
  responder_types: string[];
  available_responders: Record<string, number>;
  available_vehicles: number;
  available_equipment: string[];
  operational_status: string;
  current_deployments: string[];
}

export interface Incident {
  incident_id: string;
  location: Coordinate;
  incident_type: string;
  urgency: Urgency;
  status: IncidentStatus;
  number_of_people: number;
  first_uploaded: string;
  last_updated: string;
  needs_human_verification: boolean;
  image_url?: string | null;
  // UI-only enrichment, not always present from the API yet.
  pose?: PoseLabel;
  pose_confidence?: number;
  visible_hazards?: string;
  reasoning?: string;
  assignment?: Assignment;
}

export interface Assignment {
  assignment_id: string;
  incident_id: string;
  assigned_station_ids: string[];
  rationale: string;
  escalate_to_911: boolean;
  requires_multi_station: boolean;
  status: string;
  accepted_station_ids: string[];
  rejected_station_ids: string[];
  created_at: string;
}

export interface LogEntry {
  log_id: string;
  timestamp: string;
  incident_id?: string | null;
  event_type: string;
  summary: string;
  payload: Record<string, unknown>;
}

export interface IngestResponse {
  detection: Record<string, unknown>;
  assessment: Record<string, unknown>;
  incident: Incident;
  assignment?: Assignment | null;
}
