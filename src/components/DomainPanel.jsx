import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import StatCard from "./StatCard";
import PredictiveChart from "./PredictiveChart";

export default function DomainPanel({ domainId, domainMeta, zones, session, live }) {
  const [initial, setInitial] = useState(null);
  const [selectedZone, setSelectedZone] = useState(zones[0]?.id);
  const [selectedMetric, setSelectedMetric] = useState(Object.keys(domainMeta.metrics)[0]);
  const [forecastResult, setForecastResult] = useState(null);
  const [forecastError, setForecastError] = useState(null);

  // Seed with a REST snapshot so the grid isn't empty before the first
  // WebSocket tick arrives (sensor cadence is a few seconds).
  useEffect(() => {
    let cancelled = false;
    api
      .metricsLatest(domainId, session.role)
      .then((data) => !cancelled && setInitial(data))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [domainId, session.role]);

  const metricNames = Object.keys(domainMeta.metrics);

  const valueFor = (zoneId, metric) => {
    const liveVal = live?.[zoneId]?.[metric];
    if (liveVal) return liveVal;
    const restVal = initial?.[zoneId]?.[metric];
    return restVal ? { value: restVal.value, unit: domainMeta.metrics[metric].unit } : null;
  };

  useEffect(() => {
    let cancelled = false;
    setForecastError(null);
    api
      .predict(domainId, { role: session.role, zone: selectedZone, metric: selectedMetric, horizon: 6 })
      .then((r) => !cancelled && setForecastResult(r))
      .catch((e) => !cancelled && setForecastError(e.message));
    const interval = setInterval(() => {
      api
        .predict(domainId, { role: session.role, zone: selectedZone, metric: selectedMetric, horizon: 6 })
        .then((r) => !cancelled && setForecastResult(r))
        .catch(() => {});
    }, 6000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [domainId, selectedZone, selectedMetric, session.role]);

  const zoneName = useMemo(
    () => zones.find((z) => z.id === selectedZone)?.name || selectedZone,
    [zones, selectedZone]
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-1">{domainMeta.label} — live overview</h2>
        <p className="text-sm text-slate-400">
          Tap any tile to load its predictive forecast below. Values update in real time over WebSocket.
        </p>
      </div>

      {metricNames.map((metric) => (
        <div key={metric}>
          <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
            {metric.replace(/_/g, " ")}
          </div>
          <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${zones.length}, minmax(0,1fr))` }}>
            {zones.map((zone) => {
              const reading = valueFor(zone.id, metric);
              return (
                <StatCard
                  key={zone.id}
                  label={zone.name}
                  value={reading?.value ?? null}
                  unit={reading?.unit ?? domainMeta.metrics[metric].unit}
                  metaCfg={domainMeta.metrics[metric]}
                  selected={selectedZone === zone.id && selectedMetric === metric}
                  onClick={() => {
                    setSelectedZone(zone.id);
                    setSelectedMetric(metric);
                  }}
                />
              );
            })}
          </div>
        </div>
      ))}

      <div className="card">
        <div className="font-semibold mb-3">
          Forecast — {selectedMetric.replace(/_/g, " ")} in {zoneName}
        </div>
        {forecastError ? (
          <div className="text-sm text-slate-400">{forecastError}</div>
        ) : (
          <PredictiveChart result={forecastResult} unit={domainMeta.metrics[selectedMetric].unit} />
        )}
      </div>
    </div>
  );
}
