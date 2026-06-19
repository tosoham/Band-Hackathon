import type {
  BandGateState,
  BandEventRecord,
  HumanMessagePayload,
  ProviderStatus,
  RfpListResponse,
} from "./types";

export function backendUrl(): string {
  // Server components and route handlers should hit the in-cluster backend.
  // Client components must use the public URL the browser can reach.
  const raw =
    typeof window === "undefined"
      ? (process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL ?? "")
      : (process.env.NEXT_PUBLIC_BACKEND_URL ?? "");
  // Strip trailing slashes so a value like "https://host/" doesn't build
  // "https://host//state" (which 404s on FastAPI).
  return raw.replace(/\/+$/, "");
}

export async function fetchState(): Promise<BandGateState | null> {
  const base = backendUrl();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/state`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as BandGateState;
  } catch {
    return null;
  }
}

export async function fetchProviders(): Promise<ProviderStatus | null> {
  const base = backendUrl();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/providers`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as ProviderStatus;
  } catch {
    return null;
  }
}

export async function fetchBandEvents(): Promise<BandEventRecord[]> {
  const base = backendUrl();
  if (!base) return [];
  try {
    const res = await fetch(`${base}/band/events`, { cache: "no-store" });
    if (!res.ok) return [];
    return (await res.json()) as BandEventRecord[];
  } catch {
    return [];
  }
}

export async function fetchRfpList(): Promise<RfpListResponse | null> {
  const base = backendUrl();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/rfp/list`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as RfpListResponse;
  } catch {
    return null;
  }
}

export async function fetchBandChatReport(): Promise<string> {
  const base = backendUrl();
  if (!base) return "";
  try {
    const res = await fetch(`${base}/exports/band-chat-report`, { cache: "no-store" });
    if (!res.ok) return "";
    return await res.text();
  } catch {
    return "";
  }
}

export async function startDeliberation(questionId: string): Promise<boolean> {
  const base = backendUrl();
  if (!base) return false;
  try {
    const res = await fetch(`${base}/deliberate/${encodeURIComponent(questionId)}`, {
      method: "POST",
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function postHumanMessage(
  roomId: string,
  payload: HumanMessagePayload,
): Promise<boolean> {
  const base = backendUrl();
  if (!base) return false;
  try {
    const res = await fetch(`${base}/rooms/${encodeURIComponent(roomId)}/human-message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function loginRequest(orgSlug: string, email: string): Promise<boolean> {
  try {
    const res = await fetch(`/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ org_slug: orgSlug, email }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function uploadRfp(file: File): Promise<boolean> {
  const base = backendUrl();
  if (!base) return false;
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch(`${base}/rfp/upload`, { method: "POST", body: form });
    return res.ok;
  } catch {
    return false;
  }
}

export const ALL_AGENT_NAMES = [
  "intake_agent",
  "sales_engineer",
  "security_compliance",
  "product_capability",
  "legal_commitment_guard",
  "adversarial_reviewer",
  "human_gate",
] as const;

export type AgentName = (typeof ALL_AGENT_NAMES)[number];
