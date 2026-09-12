import { useEffect, useState } from "react";
import {
  fetchIncidentDetail,
  fetchIncidents,
  fetchLogs,
  fetchReadiness,
  ingestImage,
} from "./api";
import { DroneFeedPanel } from "./components/DroneFeedPanel";
import { Header } from "./components/Header";
import { IncidentDetailPanel } from "./components/IncidentDetailPanel";
import { IncidentQueue } from "./components/IncidentQueue";
import { ResourceManagementPanel } from "./components/ResourceManagementPanel";
import type { Incident, LogEntry, Readiness } from "./types";

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
  const [readiness, setReadiness] = useState<Readiness>();
  const [error, setError] = useState<string>();
  const [selectedId, setSelectedId] = useState<string>();
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [data, currentReadiness, currentLogs] = await Promise.all([
          fetchIncidents(),
          fetchReadiness(),
          fetchLogs(),
        ]);
        if (cancelled) return;
        setIncidents((current) =>
          data.map((item) => {
            const existing = current.find(
              (candidate) => candidate.incident_id === item.incident_id,
            );
            return {
              ...item,
              visible_hazards: existing?.visible_hazards,
              reasoning: existing?.reasoning,
              assignment: existing?.assignment,
            };
          }),
        );
        setLive(true);
        setReadiness(currentReadiness);
        setError(undefined);
        setSelectedId((current) => current ?? highestPriority(data)?.incident_id);
        setLogs(currentLogs);
      } catch (loadError) {
        if (cancelled) return;
        setLive(false);
        setError(loadError instanceof Error ? loadError.message : "Backend unavailable");
      }
    }

    load();
    const id = setInterval(load, 20_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (!selectedId || !live) return;
    let cancelled = false;
    fetchIncidentDetail(selectedId)
      .then((detail) => {
        if (!cancelled) handleIncidentUpdate(detail);
      })
      .catch((detailError: unknown) => {
        if (!cancelled) {
          setError(detailError instanceof Error ? detailError.message : "Could not load incident details");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, live]);

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
      visible_hazards: result.detection.visible_hazards,
      reasoning: result.assessment.observation_and_reasoning,
      assignment: result.assignment ?? undefined,
    };
    setIncidents((prev) => [
      incident,
      ...prev.filter((item) => item.incident_id !== incident.incident_id),
    ]);
    setSelectedId(incident.incident_id);
    setLogs(await fetchLogs());
    setError(undefined);
  }

  return (
    <div className="app-shell flex h-screen flex-col overflow-hidden">
      <Header live={live} readiness={readiness} />

      {error && (
        <div
          role="alert"
          className="border-b border-red-300 bg-red-50 px-5 py-2 text-sm font-semibold text-red-900"
        >
          {live ? "Action failed." : "Backend disconnected. No demonstration data is being substituted."}{" "}
          {error}
        </div>
      )}

      <main className="mx-auto flex w-full max-w-[1680px] flex-1 flex-col gap-4 overflow-hidden px-5 py-4 lg:px-7">
        <div className="flex shrink-0 items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-[-0.03em] text-stone-950 sm:text-3xl">
              Response command
            </h1>
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
            onError={setError}
          />
        </div>

        <div className="grid min-h-0 flex-[3] grid-cols-1 gap-4 xl:grid-cols-[1.45fr_1fr]">
          <IncidentQueue
            incidents={incidents}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <ResourceManagementPanel onError={setError} />
        </div>
      </main>
    </div>
  );
}

export default App;
