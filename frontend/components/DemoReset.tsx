"use client";

import { useState } from "react";
import Icon from "./Icon";

export default function DemoReset() {
  const [busy, setBusy] = useState(false);

  async function reset() {
    setBusy(true);
    const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/+$/, "");
    if (backendUrl) {
      try {
        await fetch(`${backendUrl}/demo/reset`, { method: "POST" });
      } catch {
        /* ignore — reload still rebuilds the client view from fresh state */
      }
    }
    // Reload to pull the rebuilt state (live) or re-mount the demo snapshot.
    window.location.reload();
  }

  return (
    <button type="button" className="resetChip" onClick={reset} disabled={busy} aria-busy={busy}>
      <Icon name="reset" size={15} />
      {busy ? "Resetting…" : "Reset demo"}
    </button>
  );
}
