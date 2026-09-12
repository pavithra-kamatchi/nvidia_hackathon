import { useEffect, useState } from "react";
import { fetchStation, updateStation } from "../api";
import type { Station } from "../types";
import { MinusIcon, PlusIcon, TruckIcon, UsersIcon, WrenchIcon } from "./icons";

function StepButton({ onClick, label, children }: { onClick: () => void; label: string; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="flex h-6 w-6 items-center justify-center rounded-full border border-neutral-200 text-neutral-600 transition hover:bg-neutral-100"
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
    <div className="flex flex-col gap-1.5 rounded-lg border border-neutral-200 px-2.5 py-1.5">
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

export function ResourceManagementPanel() {
  const [station, setStation] = useState<Station>();

  useEffect(() => {
    fetchStation().then(({ station }) => setStation(station));
  }, []);

  if (!station) {
    return <section className="h-full rounded-xl border border-neutral-200 bg-white" />;
  }

  function persist(patch: Partial<Pick<Station, "available_responders" | "available_vehicles">>) {
    if (!station) return;
    updateStation(station.station_id, patch);
  }

  function adjustResponder(type: string, delta: number) {
    setStation((prev) => {
      if (!prev) return prev;
      const next = Math.max(0, (prev.available_responders[type] ?? 0) + delta);
      const available_responders = { ...prev.available_responders, [type]: next };
      persist({ available_responders });
      return { ...prev, available_responders };
    });
  }

  function adjustVehicles(delta: number) {
    setStation((prev) => {
      if (!prev) return prev;
      const available_vehicles = Math.max(0, prev.available_vehicles + delta);
      persist({ available_vehicles });
      return { ...prev, available_vehicles };
    });
  }

  return (
    <section className="panel flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between px-5 py-3">
        <div>
          <p className="eyebrow">Readiness</p>
          <h2 className="mt-0.5 text-base font-bold text-stone-900">Resource management</h2>
        </div>
        <span className="hidden text-xs font-medium text-stone-400 sm:block">{station.name}</span>
      </div>

      <div className="min-h-0 flex-1 space-y-2.5 overflow-y-auto px-5 pb-3">
        <div className="grid grid-cols-4 gap-2">
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

        <div>
          <div className="mb-1.5 flex items-center gap-1.5 text-sm text-neutral-500">
            <WrenchIcon className="h-4 w-4" />
            Equipment
          </div>
          <div className="flex flex-wrap gap-1.5">
            {station.available_equipment.map((item) => (
              <span
                key={item}
                className="rounded-md bg-neutral-100 px-2.5 py-1 text-sm font-medium text-neutral-700"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
