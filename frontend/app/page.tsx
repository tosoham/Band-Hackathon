import Dashboard from "../components/Dashboard";
import EmptyWorkspace from "../components/EmptyWorkspace";
import type { BandEventRecord, BandGateState } from "../lib/types";

function backendBaseUrl() {
  // Strip trailing slashes — "https://host/" + "/state" would 404 as "//state".
  return (process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/+$/, "");
}

async function loadState(): Promise<BandGateState | null> {
  const baseUrl = backendBaseUrl();
  if (!baseUrl) return null;
  try {
    const response = await fetch(`${baseUrl}/state`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as BandGateState;
  } catch {
    return null;
  }
}

async function loadBandEvents(): Promise<BandEventRecord[]> {
  const baseUrl = backendBaseUrl();
  if (!baseUrl) {
    return [];
  }
  try {
    const response = await fetch(`${baseUrl}/band/events`, { cache: "no-store" });
    if (!response.ok) {
      return [];
    }
    return (await response.json()) as BandEventRecord[];
  } catch {
    return [];
  }
}

async function loadBandReport(): Promise<string> {
  const baseUrl = backendBaseUrl();
  if (!baseUrl) {
    return "";
  }
  try {
    const response = await fetch(`${baseUrl}/exports/band-chat-report`, { cache: "no-store" });
    if (!response.ok) {
      return "";
    }
    const text = await response.text();
    // The endpoint returns a JSON {"detail": ...} when the report isn't generated yet.
    return text.trimStart().startsWith("{") ? "" : text;
  } catch {
    return "";
  }
}

export default async function Home() {
  const [state, bandEvents, bandReport] = await Promise.all([
    loadState(),
    loadBandEvents(),
    loadBandReport(),
  ]);
  // Only fall back to the bare screen when the backend is unreachable. When the
  // backend is up but empty, render the full dashboard (sidebar + Intake/upload)
  // so the workspace never disappears.
  if (!state) {
    return <EmptyWorkspace offline />;
  }
  return (
    <Dashboard
      state={state}
      source="live"
      bandEvents={bandEvents}
      bandReport={bandReport}
      publicBackendUrl={(process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/+$/, "")}
    />
  );
}
