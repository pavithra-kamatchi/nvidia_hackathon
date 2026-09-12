import { useState } from "react";
import { ALL_STATUSES, dispatchIncident, fetchIncidentReport, resolveIncident, reviewIncident } from "../api";
import { STATUS_DOT, STATUS_LABEL, URGENCY_LABEL, URGENCY_TEXT, formatCoordinate } from "../lib/format";
import type { Incident, IncidentStatus } from "../types";
import {
  AlertTriangleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  FlameIcon,
  MapPinIcon,
  UsersIcon,
} from "./icons";

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
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
}: {
  incident: Incident | undefined;
  onIncidentUpdate: (incident: Incident) => void;
}) {
  const [dispatching, setDispatching] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [reporting, setReporting] = useState(false);

  if (!incident) {
    return (
      <section className="flex h-full flex-col items-center justify-center rounded-xl border border-neutral-200 bg-white p-8 text-center text-base text-neutral-400">
        Select an incident from the queue to view details.
      </section>
    );
  }

  async function handleStatusChange(status: IncidentStatus) {
    if (!incident) return;
    if (status === "resolved") {
      const updated = await resolveIncident(incident.incident_id);
      onIncidentUpdate(updated ?? { ...incident, status });
      return;
    }
    onIncidentUpdate({ ...incident, status });
  }

  async function handleDispatch() {
    if (!incident) return;
    setDispatching(true);
    const updated = await dispatchIncident(incident.incident_id, incident.assignment?.assigned_station_ids ?? []);
    setDispatching(false);
    onIncidentUpdate(updated ?? { ...incident, status: "dispatched" });
  }

  async function handleReview(approved: boolean) {
    if (!incident) return;
    setReviewing(true);
    const updated = await reviewIncident(incident.incident_id, approved);
    setReviewing(false);
    onIncidentUpdate(updated ?? { ...incident, status: approved ? "notified" : "false_positive", needs_human_verification: false });
  }

  async function handleReport() {
    if (!incident) return;
    setReporting(true);
    const report = await fetchIncidentReport(incident.incident_id);
    setReporting(false);
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
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
        <span className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-red-600">Highest priority incident</span>
        <span className="font-mono text-[11px] text-stone-400">#{incident.incident_id}</span>
      </div>

      <div className="flex shrink-0 items-center gap-4 px-5 pb-4 pt-4">
        <div className="flex items-center gap-2">
          <AlertTriangleIcon className={`h-7 w-7 ${URGENCY_TEXT[incident.urgency]}`} />
          <span className={`text-2xl font-extrabold tracking-[-0.03em] ${URGENCY_TEXT[incident.urgency]}`}>
            {URGENCY_LABEL[incident.urgency]}
          </span>
        </div>
        <div className="h-7 w-px bg-neutral-200" />
        <div className="flex items-center gap-2">
          <FlameIcon className="h-6 w-6 text-orange-500" />
          <span className="text-lg font-bold text-stone-900">{incident.incident_type}</span>
        </div>
        <ChevronRightIcon className="ml-auto h-5 w-5 text-neutral-300" />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="divide-y divide-neutral-100 border-y border-neutral-100 px-5">
          <InfoRow
            icon={<MapPinIcon className="h-5 w-5" />}
            label="Location"
            value={formatCoordinate(incident.location.latitude, incident.location.longitude)}
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
          <div className="mx-5 mt-3 rounded-lg bg-neutral-50 p-3.5">
            <div className="mb-1 text-[10px] font-extrabold uppercase tracking-[0.14em] text-stone-500">AI assessment</div>
            <p className="text-sm leading-relaxed text-stone-600">{incident.reasoning}</p>
          </div>
        )}
      </div>

      <div className="shrink-0 px-5 pb-5 pt-3">
        {incident.needs_human_verification && (
          <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <div className="text-xs font-bold text-amber-900">Human verification required</div>
            <p className="mt-1 text-xs leading-relaxed text-amber-800">Agent triage is waiting for an operator decision before notification.</p>
            <div className="mt-2 flex gap-2">
              <button type="button" onClick={() => handleReview(true)} disabled={reviewing} className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-700 disabled:opacity-60">Approve</button>
              <button type="button" onClick={() => handleReview(false)} disabled={reviewing} className="rounded-md border border-amber-300 px-3 py-1.5 text-xs font-bold text-amber-900 hover:bg-amber-100 disabled:opacity-60">Reject</button>
            </div>
          </div>
        )}
        <div className="flex items-center justify-between pb-3">
          <span className="text-xs font-bold uppercase tracking-[0.1em] text-stone-500">Status</span>
          <div className="relative">
            <select
              value={incident.status}
              onChange={(e) => handleStatusChange(e.target.value as IncidentStatus)}
              className="appearance-none rounded-lg border border-stone-200 bg-white py-2 pl-8 pr-9 text-sm font-semibold text-stone-800 outline-none focus:border-amber-500"
            >
              {ALL_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
            <span className={`pointer-events-none absolute left-3 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full ${STATUS_DOT[incident.status]}`} />
            <ChevronDownIcon className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          </div>
        </div>

        <button
          type="button"
          onClick={handleDispatch}
          disabled={dispatching}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-stone-950 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-stone-800 disabled:opacity-60"
        >
          {dispatching ? "Dispatching..." : "Dispatch Response"}
          <ChevronRightIcon className="h-5 w-5" />
        </button>
        <button type="button" onClick={handleReport} disabled={reporting} className="mt-2 flex w-full items-center justify-center rounded-lg py-2 text-xs font-bold text-stone-500 transition hover:bg-stone-50 hover:text-stone-800 disabled:opacity-60">
          {reporting ? "Preparing report..." : "Download incident report"}
        </button>
      </div>
    </section>
  );
}
