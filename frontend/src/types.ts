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
    station_type: string;
  location: Coordinate;
  responder_types: string[];
  available_responders: Record<string, number>;
  available_vehicles: number;
    available_equipment: string[];
    equipment_counts: Record<string, number>;
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
  recommended_resources: Record<string, number>;
  priority: number;
  rationale: string;
  escalate_to_911: boolean;
  requires_multi_station: boolean;
  requires_additional_support: boolean;
  needs_human_approval: boolean;
  status: string;
  accepted_station_ids: string[];
  rejected_station_ids: string[];
  created_at: string;
  decision?: "approved" | "rejected" | null;
  decided_by?: string | null;
  decided_at?: string | null;
}

export interface LogEntry {
  log_id: string;
  timestamp: string;
  incident_id?: string | null;
  actor_type: string;
  actor_id?: string | null;
  event_type: string;
  summary: string;
  payload: Record<string, unknown>;
}

export interface IngestResponse {
  detection: Detection;
  assessment: Assessment;
  incident: Incident;
  assignment?: Assignment | null;
}

export interface Detection {
  detection_id: string;
  timestamp: string;
  location: Coordinate;
  human: boolean;
  blood: boolean;
  number_of_people: number;
  visible_hazards: string;
  observations: string;
  confidence: number;
  image_url?: string | null;
}

export interface Assessment {
  assessment_id: string;
  incident_id: string;
  detection_id: string;
  timestamp: string;
  urgency: Urgency;
  incident_type: string;
  observation_and_reasoning: string;
  confidence: number;
  needs_human_verification: boolean;
}

export interface IncidentReport {
  incident: Incident;
  detections: Detection[];
  assessments: Assessment[];
  assignments: Assignment[];
  timeline: LogEntry[];
}

export interface Readiness {
  status: "ready" | "degraded";
  services: {
    mongodb: boolean;
    nemotron: boolean;
  };
}
