import type { IncidentReport } from "../types";
import {
  STATUS_LABEL,
  URGENCY_LABEL,
  formatAssignmentRationale,
  formatCoordinate,
  formatIncidentType,
  hasReportedHazard,
} from "./format";

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function readableDate(value: string | null | undefined): string {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function field(label: string, value: unknown): string {
  return `<div class="field"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`;
}

export function buildHumanIncidentReport(report: IncidentReport): string {
  const { incident } = report;
  const detection = report.detections.at(-1);
  const assessment = report.assessments.at(-1);
  const assignment = report.assignments.at(-1);
  const stations = assignment?.assigned_station_ids.length
    ? assignment.assigned_station_ids.join(", ")
    : "No station assigned";
  const resources = assignment && Object.keys(assignment.recommended_resources).length
    ? Object.entries(assignment.recommended_resources)
        .map(([name, count]) => `${formatIncidentType(name)}: ${count}`)
        .join(", ")
    : "No resources recommended";
  const verificationMessage = incident.needs_human_verification
    ? "YES — a human reviewer must verify the observation before action is taken."
    : "No additional verification is currently requested. Continue to apply normal human oversight."
  const hazards = detection?.visible_hazards ?? incident.visible_hazards;

  const timeline = report.timeline.length
    ? report.timeline
        .map(
          (entry) => `<li><time>${escapeHtml(readableDate(entry.timestamp))}</time><div><strong>${escapeHtml(formatIncidentType(entry.event_type))}</strong><p>${escapeHtml(entry.summary)}</p></div></li>`,
        )
        .join("")
    : '<p class="muted">No activity has been recorded.</p>';

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Incident Report ${escapeHtml(incident.incident_id)}</title>
  <style>
    :root { color: #1c1917; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }
    body { margin: 0; background: #f5f5f4; line-height: 1.45; }
    main { box-sizing: border-box; max-width: 900px; margin: 32px auto; padding: 36px; background: white; }
    h1, h2 { margin: 0; letter-spacing: -0.02em; }
    h1 { font-size: 30px; } h2 { margin-bottom: 14px; font-size: 19px; }
    .kicker { margin: 0 0 6px; color: #57534e; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .subtitle, .muted { color: #57534e; }
    .subtitle { margin: 8px 0 0; }
    .alert { margin: 24px 0; padding: 16px; border-left: 5px solid #d97706; background: #fffbeb; }
    .alert strong { display: block; margin-bottom: 4px; color: #78350f; }
    section { margin-top: 28px; padding-top: 24px; border-top: 1px solid #e7e5e4; }
    dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 24px; margin: 0; }
    .field { min-width: 0; } dt { color: #78716c; font-size: 12px; font-weight: 700; text-transform: uppercase; }
    dd { margin: 3px 0 0; overflow-wrap: anywhere; font-weight: 650; }
    .narrative { padding: 14px 16px; background: #fafaf9; white-space: pre-wrap; }
    ul { padding: 0; list-style: none; }
    li { display: grid; grid-template-columns: 190px 1fr; gap: 16px; padding: 12px 0; border-bottom: 1px solid #f0efed; }
    li time { color: #78716c; font-size: 13px; } li p { margin: 3px 0 0; }
    footer { margin-top: 32px; padding-top: 16px; border-top: 2px solid #292524; color: #57534e; font-size: 12px; }
    @media (max-width: 650px) { main { margin: 0; padding: 24px 18px; } dl { grid-template-columns: 1fr; } li { grid-template-columns: 1fr; gap: 3px; } }
    @media print { body { background: white; } main { max-width: none; margin: 0; padding: 0; } }
  </style>
</head>
<body>
<main>
  <header>
    <p class="kicker">SCOUT · Human Review Copy</p>
    <h1>Incident Report</h1>
    <p class="subtitle">Incident ${escapeHtml(incident.incident_id)} · Generated ${escapeHtml(new Date().toLocaleString())}</p>
  </header>

  <div class="alert"><strong>Human verification</strong>${escapeHtml(verificationMessage)}</div>

  <section>
    <h2>At a glance</h2>
    <dl>
      ${field("Urgency", URGENCY_LABEL[incident.urgency])}
      ${field("Incident type", formatIncidentType(incident.incident_type))}
      ${field("Current status", STATUS_LABEL[incident.status])}
      ${field("People observed", incident.number_of_people)}
      ${field("Location", formatCoordinate(incident.location.latitude, incident.location.longitude))}
      ${field("First reported", readableDate(incident.first_uploaded))}
      ${field("Last updated", readableDate(incident.last_updated))}
      ${field("Visible hazards", hasReportedHazard(hazards) ? hazards : "No visible hazard reported")}
    </dl>
  </section>

  <section>
    <h2>What the system observed</h2>
    <p class="narrative">${escapeHtml(detection?.observations || "No observation narrative is available.")}</p>
    <dl>
      ${field("Detection confidence", detection ? `${Math.round(detection.confidence * 100)}%` : "Not available")}
      ${field("Human detected", detection ? (detection.human ? "Yes" : "No") : "Not recorded")}
    </dl>
  </section>

  <section>
    <h2>AI assessment</h2>
    <p class="narrative">${escapeHtml(assessment?.observation_and_reasoning || incident.reasoning || "No assessment narrative is available.")}</p>
    <dl>
      ${field("Assessment confidence", assessment ? `${Math.round(assessment.confidence * 100)}%` : "Not available")}
      ${field("Review required", incident.needs_human_verification ? "Yes" : "No")}
    </dl>
  </section>

  <section>
    <h2>Recommended response</h2>
    ${assignment ? `<dl>
      ${field("Assigned station(s)", stations)}
      ${field("Recommended resources", resources)}
      ${field("911 escalation", assignment.escalate_to_911 ? "Recommended" : "Not currently recommended")}
      ${field("Multiple stations", assignment.requires_multi_station ? "Recommended" : "Not currently required")}
      ${field("Additional support", assignment.requires_additional_support ? "Recommended" : "Not currently required")}
      ${field("Human decision", assignment.decision ? formatIncidentType(assignment.decision) : "Pending")}
      ${field("Reviewed by", assignment.decided_by || "Not yet reviewed")}
      ${field("Decision time", readableDate(assignment.decided_at))}
    </dl><p class="narrative">${escapeHtml(formatAssignmentRationale(assignment.rationale))}</p>` : '<p class="muted">No response allocation has been created yet.</p>'}
  </section>

  <section>
    <h2>Activity timeline</h2>
    <ul>${timeline}</ul>
  </section>

  <footer>This report supports human decision-making. AI observations, confidence scores, and recommendations can be incorrect and must not replace emergency-service procedures or professional judgment.</footer>
</main>
</body>
</html>`;
}
