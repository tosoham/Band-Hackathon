"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [org, setOrg] = useState("demo");
  const [email, setEmail] = useState("agnik@bandgate.test");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ org_slug: org.trim(), email: email.trim() }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { error?: string } | null;
        setError(body?.error ?? "login failed");
        setPending(false);
        return;
      }
      router.push("/intake");
      router.refresh();
    } catch {
      setError("network error");
      setPending(false);
    }
  }

  return (
    <main className="loginShell">
      <section className="loginCard">
        <p className="eyebrow">Band of Agents Hackathon · Track 1</p>
        <h1>BandGate</h1>
        <p className="subtitle">Sign in to your organization to start a Promise Gate review.</p>
        <form onSubmit={submit} className="loginForm">
          <label>
            <span>Organization slug</span>
            <input
              type="text"
              value={org}
              onChange={(e) => setOrg(e.target.value)}
              autoFocus
              required
            />
          </label>
          <label>
            <span>Work email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <button type="submit" disabled={pending}>
            {pending ? "Signing in…" : "Continue"}
          </button>
          {error ? <p className="loginError">{error}</p> : null}
        </form>
        <p className="loginHelper">
          Demo credentials: <strong>demo</strong> / any email.
        </p>
      </section>
    </main>
  );
}
