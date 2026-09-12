import { useEffect, useState } from "react";
import { fetchIncidents, fetchLogs, ingestImage } from "./api";
import { DroneFeedPanel } from "./components/DroneFeedPanel";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { IncidentDetailPanel } from "./components/IncidentDetailPanel";
import { IncidentQueue } from "./components/IncidentQueue";
import { ResourceManagementPanel } from "./components/ResourceManagementPanel";
import type { Incident, LogEntry } from "./types";

const URGENCY_RANK: Record<Incident["urgency"], number> = {
  high: 0,
  medium: 1,
  low: 2,
  unclear: 3,
};

function highestPriority(incidents: Incident[]): Incident | undefined {
  return [...incidents].sort(
    (a, b) => URGENCY_RANK[a.urgency] - URGENCY_RANK[b.urgency],
  )[0];
}

function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [live, setLive] = useState(false);
  const [selectedId, setSelectedId] = useState<string>();
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const { incidents: data, live: isLive } = await fetchIncidents();
      if (cancelled) return;
      setIncidents(data);
      setLive(isLive);
      setSelectedId((current) => current ?? highestPriority(data)?.incident_id);
      setLogs(await fetchLogs());
    }

    load();
    const id = setInterval(load, 20_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const selected = incidents.find((i) => i.incident_id === selectedId);

  function handleIncidentUpdate(updated: Incident) {
    setIncidents((prev) =>
      prev.map((i) => (i.incident_id === updated.incident_id ? updated : i)),
    );
  }

  async function handleIngest(file: File, latitude: number, longitude: number) {
    const result = await ingestImage(file, latitude, longitude);
    const incident = {
      ...result.incident,
      assignment: result.assignment ?? undefined,
    };
    setIncidents((prev) => [
      incident,
      ...prev.filter((item) => item.incident_id !== incident.incident_id),
    ]);
    setSelectedId(incident.incident_id);
    setLogs(await fetchLogs());
  }

  return (
    <div className="app-shell flex h-screen flex-col overflow-hidden">
      <Header live={live} />

      <main className="mx-auto flex w-full max-w-[1680px] flex-1 flex-col gap-4 overflow-hidden px-5 py-4 lg:px-7">
        <div className="flex shrink-0 items-center justify-between gap-4">
          <div>
            <p className="eyebrow">Operations / Overview</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-[-0.03em] text-stone-950 sm:text-3xl">
              Response command
            </h1>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-stone-200 bg-white/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-stone-500 shadow-sm sm:flex">
            <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_0_3px_rgba(16,185,129,0.12)]" />
            All systems nominal
          </div>
        </div>

        <div className="grid min-h-0 flex-[8] grid-cols-1 gap-4 xl:grid-cols-[1.45fr_1fr]">
          <DroneFeedPanel
            incident={selected}
            onIngest={handleIngest}
            logs={logs}
          />
          <IncidentDetailPanel
            incident={selected}
            onIncidentUpdate={handleIncidentUpdate}
          />
        </div>

        <div className="grid min-h-0 flex-[3] grid-cols-1 gap-4 xl:grid-cols-[1.45fr_1fr]">
          <IncidentQueue
            incidents={incidents}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <ResourceManagementPanel />
        </div>
      </main>

      <div className="mx-auto w-full max-w-[1600px] shrink-0 px-6">
        <Footer />
      </div>
    </div>
  );
}

export default App;
