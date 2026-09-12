import { useState } from "react";
import {
  decideAllocation,
  fetchIncidentReport,
  resolveIncident,
  reviewIncident,
  simulateNotification,
} from "../api";
import {
  STATUS_LABEL,
  URGENCY_LABEL,
  URGENCY_TEXT,
  formatCoordinate,
} from "../lib/format";
import type { Incident } from "../types";
import {
  AlertTriangleIcon,
  ChevronRightIcon,
  FlameIcon,
  MapPinIcon,
  UsersIcon,
} from "./icons";

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3 py-2">
      <div className="mt-0.5 text-neutral-400">{icon}</div>
      <div className="w-40 shrink-0 text-base text-neutral-500">{label}</div>
      <div className="text-base font-medium text-neutral-900">{value}</div>
    </div>
  );
}

export function IncidentDetailPanel({
  incident,
  onIncidentUpdate,
  onError,
}: {
  incident: Incident | undefined;
  onIncidentUpdate: (incident: Incident) => void;
  onError: (message: string | undefined) => void;
}) {
  const [notifying, setNotifying] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [notice, setNotice] = useState<string>();

  if (!incident) {
    return (
      <section className="flex h-full flex-col items-center justify-center rounded-none border border-neutral-200 bg-white p-8 text-center text-base text-neutral-400">
        Select an incident from the queue to view details.
      </section>
    );
  }

  async function handleAllocationDecision(approved: boolean) {
    if (!incident) return;
    if (!incident.assignment) {
      onError("No allocation proposal is available for this incident.");
      return;
    }
    setReviewing(true);
    try {
      const assignment = await decideAllocation(
        incident.assignment.assignment_id,
        approved,
      );
      onIncidentUpdate({ ...incident, assignment });
      onError(undefined);
    } catch (actionError) {
      onError(actionError instanceof Error ? actionError.message : "Allocation decision failed");
    } finally {
      setReviewing(false);
    }
  }

  async function handleReview(approved: boolean) {
    if (!incident) return;
    setReviewing(true);
    try {
      const updated = await reviewIncident(incident.incident_id, approved);
      onIncidentUpdate({ ...incident, ...updated, assignment: incident.assignment });
      onError(undefined);
    } catch (actionError) {
      onError(actionError instanceof Error ? actionError.message : "Incident review failed");
    } finally {
      setReviewing(false);
    }
  }

  async function handleNotification() {
    if (!incident?.assignment) return;
    setNotifying(true);
    try {
      const result = await simulateNotification(incident.assignment.assignment_id);
      onIncidentUpdate({ ...incident, ...result.incident, assignment: incident.assignment });
      setNotice(result.message);
      onError(undefined);
    } catch (actionError) {
      onError(actionError instanceof Error ? actionError.message : "Notification simulation failed");
    } finally {
      setNotifying(false);
    }
  }

  async function handleResolve() {
    if (!incident) return;
    try {
      const updated = await resolveIncident(incident.incident_id);
      onIncidentUpdate({ ...incident, ...updated, assignment: incident.assignment });
      onError(undefined);
    } catch (actionError) {
      onError(actionError instanceof Error ? actionError.message : "Could not resolve incident");
    }
  }

  async function handleReport() {
    if (!incident) return;
    setReporting(true);
    let report;
    try {
      report = await fetchIncidentReport(incident.incident_id);
      onError(undefined);
    } catch (reportError) {
      onError(reportError instanceof Error ? reportError.message : "Could not prepare report");
      setReporting(false);
      return;
    }
    setReporting(false);
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${incident.incident_id}-report.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="panel flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between border-b border-red-100 bg-red-50/80 px-5 py-3">
        <span className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-red-600">
          Highest priority incident
        </span>
        <span className="font-mono text-[11px] text-stone-400">
          #{incident.incident_id}
        </span>
      </div>

      <div className="flex shrink-0 items-center gap-4 px-5 pb-4 pt-4">
        <div className="flex items-center gap-2">
          <AlertTriangleIcon
            className={`h-7 w-7 ${URGENCY_TEXT[incident.urgency]}`}
          />
          <span
            className={`text-2xl font-extrabold tracking-[-0.03em] ${URGENCY_TEXT[incident.urgency]}`}
          >
            {URGENCY_LABEL[incident.urgency]}
          </span>
        </div>
        <div className="h-7 w-px bg-neutral-200" />
        <div className="flex items-center gap-2">
          <FlameIcon className="h-6 w-6 text-orange-500" />
          <span className="text-lg font-bold text-stone-900">
            {incident.incident_type}
          </span>
        </div>
        <ChevronRightIcon className="ml-auto h-5 w-5 text-neutral-300" />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="divide-y divide-neutral-100 border-y border-neutral-100 px-5">
          <InfoRow
            icon={<MapPinIcon className="h-5 w-5" />}
            label="Location"
            value={formatCoordinate(
              incident.location.latitude,
              incident.location.longitude,
            )}
          />
          <InfoRow
            icon={<UsersIcon className="h-5 w-5" />}
            label="People Detected"
            value={String(incident.number_of_people)}
          />
          {incident.visible_hazards && (
            <InfoRow
              icon={<AlertTriangleIcon className="h-5 w-5" />}
              label="Visible Hazards"
              value={incident.visible_hazards}
            />
          )}
        </div>

        {incident.reasoning && (
          <div className="mx-5 mt-3 rounded-none bg-neutral-50 p-3.5">
            <div className="mb-1 text-[10px] font-extrabold uppercase tracking-[0.14em] text-stone-500">
              AI assessment
            </div>
            <p className="text-sm leading-relaxed text-stone-600">
              {incident.reasoning}
            </p>
          </div>
        )}
      </div>

      <div className="shrink-0 px-5 pb-5 pt-3">
        {incident.needs_human_verification && (
          <div className="mb-3 rounded-none border border-amber-200 bg-amber-50 p-3">
            <div className="text-xs font-bold text-amber-900">
              Human verification required
            </div>
            <p className="mt-1 text-xs leading-relaxed text-amber-800">
              Verify the observation before reviewing the resource allocation.
            </p>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={() => handleReview(true)}
                disabled={reviewing}
                className="rounded-none bg-amber-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-700 disabled:opacity-60"
              >
                Verify observation
              </button>
              <button
                type="button"
                onClick={() => handleReview(false)}
                disabled={reviewing}
                className="rounded-none border border-amber-300 px-3 py-1.5 text-xs font-bold text-amber-900 hover:bg-amber-100 disabled:opacity-60"
              >
                Mark false positive
              </button>
            </div>
          </div>
        )}
        {incident.assignment && (
          <div className="mb-3 border border-stone-200 bg-stone-50 p-3 text-xs text-stone-700">
            <div className="font-bold uppercase tracking-[0.1em] text-stone-500">
              Proposed allocation
            </div>
            <div className="mt-2">
              Stations: {incident.assignment.assigned_station_ids.join(", ") || "No available station"}
            </div>
            <div className="mt-1">{incident.assignment.rationale}</div>
            <div className="mt-1 font-semibold">
              Decision: {incident.assignment.decision ?? "awaiting operator"}
            </div>
            {!incident.needs_human_verification && !incident.assignment.decision && (
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => handleAllocationDecision(true)}
                  disabled={reviewing}
                  className="bg-stone-950 px-3 py-1.5 font-bold text-white disabled:opacity-60"
                >
                  Approve allocation
                </button>
                <button
                  type="button"
                  onClick={() => handleAllocationDecision(false)}
                  disabled={reviewing}
                  className="border border-stone-300 px-3 py-1.5 font-bold disabled:opacity-60"
                >
                  Reject allocation
                </button>
              </div>
            )}
          </div>
        )}

        {notice && (
          <div className="mb-3 border border-emerald-300 bg-emerald-50 p-2 text-xs font-semibold text-emerald-900">
            {notice}
          </div>
        )}

        <div className="flex items-center justify-between pb-3">
          <span className="text-xs font-bold uppercase tracking-[0.1em] text-stone-500">
            Status
          </span>
          <span className="border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-800">
            {STATUS_LABEL[incident.status]}
          </span>
        </div>

        {incident.assignment?.decision === "approved" && incident.status !== "notified" && (
          <button
            type="button"
            onClick={handleNotification}
            disabled={notifying}
            className="flex w-full items-center justify-center gap-2 bg-stone-950 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-stone-800 disabled:opacity-60"
          >
            {notifying ? "Simulating..." : "Simulate station notification"}
            <ChevronRightIcon className="h-5 w-5" />
          </button>
        )}
        {(["notified", "dispatched", "in_progress"] as const).includes(
          incident.status as "notified" | "dispatched" | "in_progress",
        ) && (
          <button
            type="button"
            onClick={handleResolve}
            className="mt-2 flex w-full items-center justify-center border border-stone-300 py-2 text-xs font-bold text-stone-700"
          >
            Mark incident resolved
          </button>
        )}
        <button
          type="button"
          onClick={handleReport}
          disabled={reporting}
          className="mt-2 flex w-full items-center justify-center rounded-none py-2 text-xs font-bold text-stone-500 transition hover:bg-stone-50 hover:text-stone-800 disabled:opacity-60"
        >
          {reporting ? "Preparing report..." : "Download incident report"}
        </button>
      </div>
    </section>
  );
}
