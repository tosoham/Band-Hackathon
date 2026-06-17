import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => null)) as {
    org_slug?: string;
    email?: string;
  } | null;
  if (!body?.org_slug || !body?.email) {
    return NextResponse.json({ error: "org_slug and email required" }, { status: 400 });
  }

  const backend = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL;
  let token = `demo:${body.org_slug}:${body.email}`;
  let org = "SentinelAI Security Platform";
  if (backend) {
    try {
      const res = await fetch(`${backend}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const data = (await res.json()) as { token?: string; org?: string };
        token = data.token ?? token;
        org = data.org ?? org;
      } else if (res.status === 400) {
        return NextResponse.json({ error: "invalid credentials" }, { status: 400 });
      }
    } catch {
      // Backend unreachable — fall back to local cookie stub so the demo still works.
    }
  }
  const response = NextResponse.json({ ok: true, org, token });
  response.cookies.set("bandgate_session", token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return response;
}
