import { useEffect, useState } from "react";
import { formatDate, formatTime } from "../lib/format";
import { ActivityIcon, CpuIcon, MenuIcon, WifiIcon } from "./icons";

function StatusPill({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2 text-xs font-semibold text-stone-600">
      <span className="text-stone-400">{icon}</span>
      <span>{label}</span>
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
    </div>
  );
}

export function Header({ live }: { live: boolean }) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="flex shrink-0 items-center justify-between gap-4 border-b border-stone-200/80 bg-[#faf9f7]/95 px-5 py-3.5 backdrop-blur lg:px-7">
      <div className="flex items-center gap-4">
        <button
          type="button"
          aria-label="Open menu"
          className="rounded-lg border border-stone-200 bg-white p-2 text-stone-600 shadow-sm transition hover:border-stone-300 hover:bg-stone-50"
        >
          <MenuIcon className="h-6 w-6" />
        </button>

        <div className="flex items-center gap-3">
          <img
            src="/logo.png"
            alt="SCOUT"
            className="h-10 w-10 object-contain"
          />
          <div className="leading-tight">
            <div className="text-xl font-extrabold tracking-[-0.04em] text-stone-950">
              SCOUT<span className="text-amber-600">.</span>
            </div>
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
              AI for Public Safety
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 sm:gap-6">
        <div className="hidden items-center gap-5 sm:flex">
          <StatusPill icon={<CpuIcon className="h-5 w-5" />} label="Local AI" />
          <StatusPill
            icon={<WifiIcon className="h-5 w-5" />}
            label={live ? "Live Backend" : "Offline Mode"}
          />
          <StatusPill
            icon={<ActivityIcon className="h-5 w-5" />}
            label="Active"
          />
        </div>

        <div className="h-9 w-px bg-neutral-200" />

        <div className="text-right leading-tight">
          <div className="text-sm font-bold text-stone-900 sm:text-base">
            {formatTime(now)}
          </div>
          <div className="text-[11px] font-medium text-stone-400">
            {formatDate(now)}
          </div>
        </div>
      </div>
    </header>
  );
}
