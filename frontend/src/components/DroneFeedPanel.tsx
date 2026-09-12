import { useState } from "react";
import type { ChangeEvent } from "react";
import { apiUrl } from "../api";
import { formatCoordinate } from "../lib/format";
import type { Incident, LogEntry } from "../types";
import { CompassIcon, MapPinIcon, UploadIcon } from "./icons";

export function DroneFeedPanel({
  incident,
  logs,
  onIngest,
}: {
  incident: Incident | undefined;
  logs: LogEntry[];
  onIngest: (file: File, latitude: number, longitude: number) => Promise<void>;
}) {
  const latestLog = logs[0];
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const feedImage = incident?.image_url
    ? apiUrl(incident.image_url)
    : "/live-feed.png";

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    setIsUploading(true);
    try {
      await onIngest(
        file,
        incident?.location.latitude ?? 42.4483,
        incident?.location.longitude ?? -76.4791,
      );
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : "Image upload failed",
      );
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  return (
    <section className="panel flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-stone-200 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.08em] text-stone-900">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-600" />
          Live Feed
        </div>
        <div className="hidden items-center gap-2 text-xs text-stone-500 sm:flex">
          <MapPinIcon className="h-4 w-4" />
          Location
          <span className="font-bold text-stone-900">
            {incident
              ? formatCoordinate(
                  incident.location.latitude,
                  incident.location.longitude,
                )
              : "—"}
          </span>
        </div>
      </div>

      <div className="relative min-h-0 w-full flex-1 overflow-hidden bg-neutral-900">
        <img
          src={feedImage}
          alt="Image selected for triage"
          className="absolute inset-0 h-full w-full object-contain brightness-[0.88] saturate-[0.85]"
        />

        <label
          className={`absolute right-4 top-4 flex min-h-10 cursor-pointer items-center gap-2 rounded-none bg-amber-500 px-3 py-2 text-[10px] font-extrabold uppercase tracking-[0.12em] text-stone-950 shadow-lg transition hover:bg-amber-400 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-amber-700 ${
            isUploading ? "pointer-events-none opacity-80" : ""
          }`}
          title="Upload an image for triage"
        >
          <UploadIcon className="h-4 w-4 shrink-0" />
          <span>{isUploading ? "Analyzing..." : "Upload image"}</span>
          <input
            type="file"
            accept="image/*"
            onChange={handleUpload}
            disabled={isUploading}
            className="sr-only"
          />
        </label>

        {uploadError && (
          <div
            role="alert"
            className="absolute right-4 top-16 max-w-64 rounded-none border border-red-300 bg-red-50 px-3 py-2 text-xs font-semibold text-red-800 shadow-lg"
          >
            {uploadError}
          </div>
        )}

        <div className="absolute inset-x-0 bottom-0 flex items-end justify-between px-4 py-3 text-sm text-neutral-200">
          <div className="rounded-none border border-white/10 bg-black/35 px-2.5 py-1.5 text-[11px] font-medium backdrop-blur-sm">
            DJI M3T&nbsp;&nbsp;|&nbsp;&nbsp;Alt: 120
            m&nbsp;&nbsp;|&nbsp;&nbsp;Zoom: 3.2x
          </div>

          <div className="flex flex-col items-end gap-1.5">
            <CompassIcon className="h-5 w-5 text-white" />
            <div className="flex items-center gap-1.5 rounded-none border border-white/10 bg-black/35 px-2.5 py-1.5 text-[11px] backdrop-blur-sm">
              <span>0</span>
              <span>0.5</span>
              <span>1&nbsp;km</span>
            </div>
            <div className="h-0.5 w-20 bg-white/70" />
          </div>
        </div>

        {latestLog && (
          <div className="absolute bottom-4 left-1/2 hidden max-w-[48%] -translate-x-1/2 rounded-none border border-white/10 bg-black/45 px-3 py-2 text-center text-[10px] text-white/80 backdrop-blur-sm md:block">
            <span className="mr-1.5 font-bold uppercase tracking-[0.12em] text-amber-300">
              Agent activity
            </span>
            {latestLog.summary}
          </div>
        )}
      </div>
    </section>
  );
}
