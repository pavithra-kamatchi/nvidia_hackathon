import { STATUS_LABEL, STATUS_PILL, URGENCY_DOT, formatTime } from "../lib/format";
import type { Incident } from "../types";
import { ChevronRightIcon } from "./icons";

export function IncidentQueue({
  incidents,
  selectedId,
  onSelect,
}: {
  incidents: Incident[];
  selectedId: string | undefined;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="panel flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between px-5 py-3">
        <div>
          <p className="eyebrow">Triage queue</p>
          <h2 className="mt-0.5 text-base font-bold text-stone-900">Incidents <span className="text-stone-400">{incidents.length}</span></h2>
        </div>
        <ChevronRightIcon className="h-4 w-4 text-stone-300" />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <table className="w-full border-collapse text-base">
          <thead>
            <tr className="sticky top-0 border-y border-stone-100 bg-stone-50/80 text-left text-[10px] font-bold uppercase tracking-[0.1em] text-stone-400">
              <th className="px-5 py-2 font-semibold">Time</th>
              <th className="px-2 py-2 font-semibold">ID</th>
              <th className="px-2 py-2 font-semibold">Type</th>
              <th className="px-5 py-2 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((incident) => (
              <tr
                key={incident.incident_id}
                onClick={() => onSelect(incident.incident_id)}
                className={`cursor-pointer border-b border-stone-100 last:border-0 transition hover:bg-amber-50/50 ${
                  selectedId === incident.incident_id ? "bg-amber-50/70 shadow-[inset_3px_0_0_#d97706]" : ""
                }`}
              >
                <td className="px-5 py-2">
                  <span className="flex items-center gap-2 text-xs font-medium text-stone-700">
                    <span className={`h-2.5 w-2.5 rounded-full ${URGENCY_DOT[incident.urgency]}`} />
                    {formatTime(new Date(incident.first_uploaded))}
                  </span>
                </td>
                <td className="px-2 py-2 text-xs text-stone-500">#{incident.incident_id}</td>
                <td className="px-2 py-2 text-xs font-medium text-stone-700">{incident.incident_type}</td>
                <td className="px-5 py-2">
                  <span className={`inline-flex rounded-md px-2 py-1 text-[11px] font-bold ${STATUS_PILL[incident.status]}`}>
                    {STATUS_LABEL[incident.status]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
