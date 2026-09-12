import type { KeyboardEvent } from "react";
import {
  STATUS_LABEL,
  STATUS_PILL,
  URGENCY_DOT,
  URGENCY_LABEL,
  formatIncidentType,
  formatTime,
} from "../lib/format";
import type { Incident } from "../types";

export function IncidentQueue({
  incidents,
  selectedId,
  onSelect,
}: {
  incidents: Incident[];
  selectedId: string | undefined;
  onSelect: (id: string) => void;
}) {
  function handleRowKeyDown(
    event: KeyboardEvent<HTMLTableRowElement>,
    incidentId: string,
  ) {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    onSelect(incidentId);
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center px-1 pb-2">
        <h2 className="text-base font-bold text-stone-900">
          Incidents Queue{" "}
          <span className="text-stone-400">({incidents.length})</span>
        </h2>
      </div>

      <section className="panel flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="incident-queue-scroll min-h-0 flex-1 overflow-y-auto">
          <table className="w-full border-collapse text-base">
            <thead>
              <tr className="sticky top-0 border-y border-stone-100 bg-stone-50/80 text-left text-[10px] font-bold uppercase tracking-[0.1em] text-stone-400">
                <th scope="col" className="px-5 py-2 font-semibold">Time</th>
                <th scope="col" className="px-2 py-2 font-semibold">ID</th>
                <th scope="col" className="px-2 py-2 font-semibold">Type</th>
                <th scope="col" className="px-5 py-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((incident) => {
                const displayStatus =
                  incident.assignment?.decision === "rejected"
                    ? "Allocation Rejected"
                    : STATUS_LABEL[incident.status];
                const selected = selectedId === incident.incident_id;
                const incidentType = formatIncidentType(incident.incident_type);

                return (
                  <tr
                    key={incident.incident_id}
                    onClick={() => onSelect(incident.incident_id)}
                    onKeyDown={(event) => handleRowKeyDown(event, incident.incident_id)}
                    tabIndex={0}
                    aria-selected={selected}
                    aria-label={`${incidentType}, ${URGENCY_LABEL[incident.urgency]} urgency, ${displayStatus}`}
                    className={`cursor-pointer border-b border-stone-100 outline-none transition last:border-0 hover:bg-amber-50/50 focus-visible:bg-amber-50 focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-inset ${
                      selected
                        ? "bg-amber-50/70 shadow-[inset_3px_0_0_#d97706]"
                        : ""
                    }`}
                  >
                    <td className="px-5 py-2">
                      <span className="flex items-center gap-2 text-xs font-medium text-stone-700">
                        <span
                          aria-hidden="true"
                          className={`h-2.5 w-2.5 rounded-full ${URGENCY_DOT[incident.urgency]}`}
                        />
                        <span className="sr-only">{URGENCY_LABEL[incident.urgency]} urgency, </span>
                        {formatTime(new Date(incident.first_uploaded))}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-xs text-stone-500">
                      #{incident.incident_id}
                    </td>
                    <td className="px-2 py-2 text-xs font-medium text-stone-700">
                      {incidentType}
                    </td>
                    <td className="px-5 py-2">
                      <span
                        className={`inline-flex rounded-none px-2 py-1 text-[11px] font-bold ${STATUS_PILL[incident.status]}`}
                      >
                        {displayStatus}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
