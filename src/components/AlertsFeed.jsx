import { useEffect, useState } from "react";
import { api } from "../api";

const SEVERITY_BADGE = { critical: "badge-critical", warning: "badge-warning" };

export default function AlertsFeed({ session, liveAlerts }) {
  const [history, setHistory] = useState([]);
  const [severity, setSeverity] = useState("");

  useEffect(() => {
    api
      .alerts({ role: session.role, severity: severity || undefined, limit: 50 })
      .then(setHistory)
      .catch(() => {});
  }, [session.role, severity]);

  // Live alerts arrive newest-first already; merge without duplicating
  // anything the initial history fetch already included.
  const seen = new Set(history.map((a) => `${a.domain}:${a.zone}:${a.metric}:${a.timestamp}`));
  const merged = [
    ...liveAlerts.filter((a) => !seen.has(`${a.domain}:${a.zone}:${a.metric}:${a.timestamp}`)),
    ...history,
  ].filter((a) => !severity || a.severity === severity);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Predictive Alerts</h2>
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="bg-panelAlt border border-border rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">All severities</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      {merged.length === 0 && (
        <div className="card text-sm text-slate-400">No alerts yet — the anomaly detector fires on
        threshold breaches and statistical spikes as sensor data streams in.</div>
      )}

      <div className="space-y-2">
        {merged.map((a, i) => (
          <div key={i} className="card flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`badge ${SEVERITY_BADGE[a.severity]}`}>{a.severity}</span>
                <span className="text-sm font-semibold">{a.domain.replace("_", " ")}</span>
                <span className="text-sm text-slate-400">· {a.zone.replace("_", " ")}</span>
              </div>
              <div className="text-sm text-slate-300">{a.reason}</div>
            </div>
            <div className="text-right">
              <div className="font-mono text-lg">{a.value}</div>
              <div className="text-xs text-slate-500">{new Date(a.timestamp).toLocaleTimeString()}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
