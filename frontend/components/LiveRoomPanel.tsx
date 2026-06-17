"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ALL_AGENT_NAMES, postHumanMessage, startDeliberation } from "../lib/api";
import { subscribeToRoom } from "../lib/sse";
import type { BandEventRecord, HumanGateAction } from "../lib/types";

type Props = {
  questionId: string;
  rfpId: string;
  publicBackendUrl: string;
};

const ROOM_KEY = (rfpId: string) => rfpId || "demo-room";

const AGENT_DISPLAY: Record<string, { label: string; tone: string }> = {
  intake_agent: { label: "Intake Agent", tone: "agent-blue" },
  sales_engineer: { label: "Sales Engineer", tone: "agent-yellow" },
  security_compliance: { label: "Security & Compliance", tone: "agent-green" },
  product_capability: { label: "Product Capability", tone: "agent-purple" },
  legal_commitment_guard: { label: "Legal / Commitment Guard", tone: "agent-red" },
  adversarial_reviewer: { label: "Adversarial Reviewer", tone: "agent-orange" },
  human_gate: { label: "Human Gate", tone: "agent-black" },
  orchestrator: { label: "Orchestrator", tone: "agent-grey" },
};

export default function LiveRoomPanel({ questionId, rfpId, publicBackendUrl }: Props) {
  const [events, setEvents] = useState<BandEventRecord[]>([]);
  const [draft, setDraft] = useState("");
  const [mentions, setMentions] = useState<string[]>([]);
  const [action, setAction] = useState<HumanGateAction>("comment");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const roomId = useMemo(() => ROOM_KEY(rfpId), [rfpId]);

  useEffect(() => {
    if (!publicBackendUrl) return;
    const subscription = subscribeToRoom(publicBackendUrl, roomId, questionId, (event) => {
      setEvents((prev) => {
        const next = [...prev, event];
        if (next.length > 400) next.splice(0, next.length - 400);
        return next;
      });
    });
    return () => subscription.close();
  }, [publicBackendUrl, roomId, questionId]);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events.length]);

  async function handleStartDeliberation() {
    setBusy(true);
    setFeedback(null);
    const ok = await startDeliberation(questionId);
    setFeedback(ok ? "Deliberation started." : "Could not start deliberation.");
    setBusy(false);
  }

  async function submitHumanMessage(submitAction: HumanGateAction) {
    if (!draft.trim() && submitAction !== "approve") {
      setFeedback("Message body required.");
      return;
    }
    setBusy(true);
    setFeedback(null);
    const ok = await postHumanMessage(roomId, {
      question_id: questionId,
      content: draft.trim() || `${submitAction.replaceAll("_", " ")} signal`,
      action: submitAction,
      mentions,
    });
    setBusy(false);
    setFeedback(ok ? `${submitAction.replaceAll("_", " ")} sent.` : "Send failed.");
    if (ok && submitAction !== "comment") {
      setDraft("");
    }
  }

  const lastEvent = events[events.length - 1];

  return (
    <section className="livePanel" aria-label={`Live Band room for ${questionId}`}>
      <header className="livePanelHeader">
        <div>
          <h2>Live Band Room</h2>
          <p>
            Room: <code>{roomId}</code>
            {lastEvent ? <> · last event {new Date(lastEvent.timestamp).toLocaleTimeString()}</> : null}
          </p>
        </div>
        <div className="livePanelActions">
          <button type="button" onClick={handleStartDeliberation} disabled={busy}>
            Start deliberation
          </button>
        </div>
      </header>
      <div className="liveStream" ref={containerRef}>
        {events.length === 0 ? (
          <p className="liveEmpty">
            No events yet. Click <strong>Start deliberation</strong> to kick off the six-agent room.
          </p>
        ) : (
          events.map((event, index) => (
            <article
              key={`${event.timestamp}-${index}-${event.agent}`}
              className={`liveTurn ${AGENT_DISPLAY[event.agent]?.tone ?? "agent-grey"}`}
            >
              <header>
                <span className="liveAgent">
                  {AGENT_DISPLAY[event.agent]?.label ?? event.agent}
                </span>
                <span className="liveMeta">
                  {event.event_type.replaceAll("_", " ")}
                  {event.payload && typeof event.payload === "object" && "round_no" in event.payload
                    ? ` · round ${(event.payload as { round_no?: number }).round_no}`
                    : ""}
                </span>
              </header>
              <p>{event.summary}</p>
              {event.payload && typeof event.payload === "object" && "mentions" in event.payload ? (
                <small>
                  →{" "}
                  {((event.payload as { mentions?: string[] }).mentions ?? []).join(", ") || "no mentions"}
                </small>
              ) : null}
            </article>
          ))
        )}
      </div>
      <footer className="liveComposer">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type a message, @mention an agent, then approve / push back / escalate…"
          rows={2}
        />
        <div className="composerRow">
          <label>
            <span>Mention</span>
            <select
              multiple
              value={mentions}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions).map((opt) => opt.value);
                setMentions(selected);
              }}
            >
              {ALL_AGENT_NAMES.map((agent) => (
                <option key={agent} value={agent}>
                  {AGENT_DISPLAY[agent]?.label ?? agent}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Action</span>
            <select value={action} onChange={(e) => setAction(e.target.value as HumanGateAction)}>
              <option value="comment">Comment</option>
              <option value="approve">Approve</option>
              <option value="approve_with_edits">Approve with edits</option>
              <option value="push_back">Push back</option>
              <option value="escalate">Escalate</option>
              <option value="reject">Reject</option>
            </select>
          </label>
          <button type="button" onClick={() => submitHumanMessage(action)} disabled={busy}>
            Send as Human Gate
          </button>
        </div>
        {feedback ? <p className="liveFeedback">{feedback}</p> : null}
      </footer>
    </section>
  );
}
