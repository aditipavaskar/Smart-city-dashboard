import { useEffect, useRef, useState } from "react";
import { wsUrl } from "./api";

/**
 * Subscribes to the real-time stream for the given auth token and keeps:
 *  - `latest`: { [domain]: { [zone]: { [metric]: {value, unit, timestamp} } } }
 *  - `alerts`: most-recent-first array of live alert events
 *  - `status`: "connecting" | "open" | "closed"
 *
 * Auto-reconnects with backoff if the connection drops, since this is meant
 * to run unattended on an ops-room screen.
 */
export function useCityStream(token) {
  const [latest, setLatest] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState("connecting");
  const retryDelay = useRef(1000);

  useEffect(() => {
    if (!token) return undefined;
    let ws;
    let closedByEffectCleanup = false;
    let retryTimer;

    const connect = () => {
      setStatus("connecting");
      ws = new WebSocket(wsUrl(token));

      ws.onopen = () => {
        setStatus("open");
        retryDelay.current = 1000;
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "reading") {
          setLatest((prev) => ({
            ...prev,
            [msg.domain]: {
              ...prev[msg.domain],
              [msg.zone]: {
                ...prev[msg.domain]?.[msg.zone],
                [msg.metric]: { value: msg.value, unit: msg.unit, timestamp: msg.timestamp },
              },
            },
          }));
        } else if (msg.type === "alert") {
          setAlerts((prev) => [msg, ...prev].slice(0, 100));
        }
      };

      ws.onclose = () => {
        setStatus("closed");
        if (!closedByEffectCleanup) {
          retryTimer = setTimeout(connect, retryDelay.current);
          retryDelay.current = Math.min(retryDelay.current * 1.6, 15000);
        }
      };

      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      closedByEffectCleanup = true;
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, [token]);

  return { latest, alerts, status };
}
