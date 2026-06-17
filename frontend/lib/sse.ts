import type { BandEventRecord } from "./types";

export type RoomEventHandler = (event: BandEventRecord) => void;

export type RoomSubscription = {
  close: () => void;
};

const RECONNECT_DELAYS = [500, 1000, 2000, 4000, 8000];

export function subscribeToRoom(
  baseUrl: string,
  roomId: string,
  questionId: string | null,
  onEvent: RoomEventHandler,
): RoomSubscription {
  let stopped = false;
  let reconnectIndex = 0;
  let source: EventSource | null = null;

  const url = `${baseUrl.replace(/\/$/, "")}/rooms/${encodeURIComponent(roomId)}/events${
    questionId ? `?question_id=${encodeURIComponent(questionId)}` : ""
  }`;

  const connect = () => {
    if (stopped) return;
    source = new EventSource(url);
    source.addEventListener("band-event", (raw) => {
      reconnectIndex = 0;
      try {
        const data = JSON.parse((raw as MessageEvent).data) as BandEventRecord;
        onEvent(data);
      } catch (err) {
        console.warn("[sse] dropped malformed band-event", err);
      }
    });
    source.onerror = () => {
      source?.close();
      source = null;
      if (stopped) return;
      const delay = RECONNECT_DELAYS[Math.min(reconnectIndex, RECONNECT_DELAYS.length - 1)];
      reconnectIndex += 1;
      setTimeout(connect, delay);
    };
  };

  connect();

  return {
    close: () => {
      stopped = true;
      source?.close();
      source = null;
    },
  };
}
