import type { Incident, Station } from "../types";

export const MOCK_STATION: Station = {
  station_id: "stn-001",
  name: "Station 12 — Ithaca Falls",
  location: { latitude: 42.4483, longitude: -76.4791 },
  responder_types: ["EMT", "Firefighter", "Police"],
  available_responders: { EMT: 4, Firefighter: 6, Police: 3 },
  available_vehicles: 5,
  available_equipment: ["Medical Kit", "Thermal Camera", "Extraction Gear", "Water Pump"],
  operational_status: "available",
  current_deployments: [],
};

export const MOCK_INCIDENTS: Incident[] = [
  {
    incident_id: "INC-2024-0817-001",
    location: { latitude: 42.4471, longitude: -76.4804 },
    incident_type: "Wildfire",
    urgency: "high",
    status: "new",
    number_of_people: 1,
    first_uploaded: "2024-08-17T10:42:00Z",
    last_updated: "2024-08-17T10:42:00Z",
    needs_human_verification: true,
    pose: "sitting",
    pose_confidence: 0.87,
    visible_hazards: "Active fire, smoke",
    reasoning:
      "Person detected near active fire zone. Person is within close proximity to active wildfire, with high risk due to visible smoke and fire spread in the area.",
  },
  {
    incident_id: "INC-2024-0817-002",
    location: { latitude: 42.4502, longitude: -76.4839 },
    incident_type: "Wildfire",
    urgency: "medium",
    status: "in_progress",
    number_of_people: 0,
    first_uploaded: "2024-08-17T10:36:00Z",
    last_updated: "2024-08-17T10:39:00Z",
    needs_human_verification: false,
    visible_hazards: "Smoke, low visibility",
    reasoning:
      "Smoke plume growing but no people detected in frame. Monitoring for spread toward the access road.",
  },
  {
    incident_id: "INC-2024-0817-003",
    location: { latitude: 42.4418, longitude: -76.4761 },
    incident_type: "Blocked Road",
    urgency: "low",
    status: "new",
    number_of_people: 0,
    first_uploaded: "2024-08-17T10:28:00Z",
    last_updated: "2024-08-17T10:28:00Z",
    needs_human_verification: false,
    visible_hazards: "Fallen debris",
    reasoning:
      "Fallen tree limb partially blocking single-lane access road. No injuries observed.",
  },
];
