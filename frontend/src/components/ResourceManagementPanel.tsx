import { useEffect, useState } from "react";
import { fetchStations, updateStation } from "../api";
import type { Station } from "../types";
import {
  ChevronRightIcon,
  MinusIcon,
  PlusIcon,
  TruckIcon,
  UsersIcon,
  WrenchIcon,
  XIcon,
} from "./icons";

function StepButton({
  onClick,
  label,
  children,
}: {
  onClick: () => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="flex h-6 w-6 items-center justify-center rounded-none border border-neutral-200 text-neutral-600 transition hover:bg-neutral-100"
    >
      {children}
    </button>
  );
}

function Counter({
  icon,
  label,
  value,
  onDecrement,
  onIncrement,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  onDecrement: () => void;
  onIncrement: () => void;
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-none border border-neutral-200 px-2.5 py-1.5">
      <div className="flex items-center gap-1.5 text-neutral-500">
        {icon}
        <span className="truncate text-sm">{label}</span>
      </div>
      <div className="flex items-center justify-between">
        <StepButton label={`Decrease ${label}`} onClick={onDecrement}>
          <MinusIcon className="h-3 w-3" />
        </StepButton>
        <span className="text-lg font-semibold text-neutral-900">{value}</span>
        <StepButton label={`Increase ${label}`} onClick={onIncrement}>
          <PlusIcon className="h-3 w-3" />
        </StepButton>
      </div>
    </div>
  );
}

export function ResourceManagementPanel({
  onError,
}: {
  onError: (message: string | undefined) => void;
}) {
  const [station, setStation] = useState<Station>();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    fetchStations()
      .then((stations) => {
        setStation(stations[0]);
        if (stations.length === 0) onError("No stations are registered in MongoDB.");
      })
      .catch((error: unknown) => {
        onError(error instanceof Error ? error.message : "Could not load stations");
      });
  }, [onError]);

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  if (!station) {
    return (
      <section className="panel flex h-full items-center justify-center p-4 text-sm text-stone-500">
        <button
          type="button"
          disabled
          className="border border-stone-200 bg-stone-50 px-4 py-3 font-semibold text-stone-400"
        >
          No station resources available
        </button>
      </section>
    );
  }

  async function persist(
    patch: Partial<
      Pick<Station, "available_responders" | "available_vehicles">
    >,
  ) {
    if (!station) return;
    try {
      const updated = await updateStation(station.station_id, patch);
      setStation(updated);
      onError(undefined);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Station update failed");
    }
  }

  function adjustResponder(type: string, delta: number) {
    if (!station) return;
    const next = Math.max(0, (station.available_responders[type] ?? 0) + delta);
    void persist({
      available_responders: {
        ...station.available_responders,
        [type]: next,
      },
    });
  }

  function adjustVehicles(delta: number) {
    if (!station) return;
    void persist({
      available_vehicles: Math.max(0, station.available_vehicles + delta),
    });
  }

  return (
    <section className="panel flex h-full items-center justify-center overflow-hidden p-4">
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="flex w-full max-w-sm items-center justify-between gap-4 border border-stone-200 bg-white px-5 py-4 text-left shadow-sm transition hover:border-stone-300 hover:bg-stone-50"
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center border border-stone-200 bg-stone-50 text-stone-600">
            <WrenchIcon className="h-5 w-5" />
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-bold text-stone-950">
              Manage station resources
            </span>
            <span className="block truncate text-xs font-medium text-stone-500">
              {station.name}
            </span>
          </span>
        </span>
        <ChevronRightIcon className="h-5 w-5 shrink-0 text-stone-400" />
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/45 px-4 backdrop-blur-sm"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setIsOpen(false);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="resource-management-title"
            className="flex max-h-[86dvh] w-full max-w-2xl flex-col overflow-hidden border border-stone-200 bg-white shadow-2xl"
          >
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-stone-100 px-5 py-4">
              <div>
                <p className="eyebrow">Readiness</p>
                <h2
                  id="resource-management-title"
                  className="mt-1 text-xl font-bold text-stone-950"
                >
                  Manage station resources
                </h2>
                <p className="mt-1 text-sm font-medium text-stone-500">
                  {station.name}
                </p>
              </div>
              <button
                type="button"
                aria-label="Close resource management"
                onClick={() => setIsOpen(false)}
                className="flex h-9 w-9 shrink-0 items-center justify-center border border-stone-200 text-stone-500 transition hover:bg-stone-50 hover:text-stone-900"
              >
                <XIcon className="h-5 w-5" />
              </button>
            </div>

            <div className="incident-queue-scroll min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-bold text-stone-800">
                  <UsersIcon className="h-4 w-4 text-stone-500" />
                  Responders and vehicles
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {station.responder_types.map((type) => (
                    <Counter
                      key={type}
                      icon={<UsersIcon className="h-4 w-4" />}
                      label={type}
                      value={station.available_responders[type] ?? 0}
                      onDecrement={() => adjustResponder(type, -1)}
                      onIncrement={() => adjustResponder(type, 1)}
                    />
                  ))}
                  <Counter
                    icon={<TruckIcon className="h-4 w-4" />}
                    label="Vehicles"
                    value={station.available_vehicles}
                    onDecrement={() => adjustVehicles(-1)}
                    onIncrement={() => adjustVehicles(1)}
                  />
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-bold text-stone-800">
                  <WrenchIcon className="h-4 w-4 text-stone-500" />
                  Equipment inventory
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {station.available_equipment.map((item) => (
                    <span
                      key={item}
                      className="bg-neutral-100 px-2.5 py-1 text-sm font-medium text-neutral-700"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex shrink-0 items-center justify-between gap-3 border-t border-stone-100 bg-stone-50 px-5 py-3">
              <span className="text-xs font-medium text-stone-500">
                Updates save immediately to station state.
              </span>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="bg-stone-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-stone-800"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
