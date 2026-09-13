import { useMemo } from "react";

/**
 * Lightweight SVG map: projects zone lat/lng into a viewBox and colors each
 * marker by the worst live severity across whatever domains the current
 * role can see. This keeps the demo self-contained (no API key required).
 *
 * Swap-in point for production: replace the <svg> below with a real
 * react-leaflet / Google Maps / Mapbox GL component, keeping the same
 * `zones` + `severityByZone` props — the projection math here is only
 * standing in for what the map SDK would normally do for you.
 */
function project(zones) {
  const lats = zones.map((z) => z.lat);
  const lngs = zones.map((z) => z.lng);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
  const pad = 60;
  const W = 640, H = 380;
  return zones.map((z) => {
    const x = pad + ((z.lng - minLng) / (maxLng - minLng || 1)) * (W - 2 * pad);
    // invert y: higher latitude = further north = higher on screen
    const y = H - pad - ((z.lat - minLat) / (maxLat - minLat || 1)) * (H - 2 * pad);
    return { ...z, x, y };
  });
}

const SEVERITY_COLOR = { critical: "#ef5959", warning: "#f5b942", ok: "#5fd68e", unknown: "#3fd0c9" };

function worstSeverity(zoneId, domains, live) {
  let worst = "unknown";
  const rank = { ok: 0, unknown: 0, warning: 1, critical: 2 };
  for (const domain of domains) {
    const metrics = live?.[domain.id]?.[zoneId];
    if (!metrics) continue;
    for (const [metric, reading] of Object.entries(metrics)) {
      const cfg = domain.metrics[metric];
      if (!cfg || reading?.value == null) continue;
      const bad = cfg.higher_is_worse ? reading.value >= cfg.critical : reading.value <= cfg.critical;
      const warn = cfg.higher_is_worse ? reading.value >= cfg.warn : reading.value <= cfg.warn;
      const sev = bad ? "critical" : warn ? "warning" : "ok";
      if (rank[sev] > rank[worst]) worst = sev;
    }
  }
  return worst;
}

export default function CityMapView({ zones, domains, live, onSelectZone }) {
  const projected = useMemo(() => project(zones), [zones]);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="font-semibold">City Overview Map</div>
        <div className="flex gap-3 text-xs text-slate-400">
          {Object.entries(SEVERITY_COLOR)
            .filter(([k]) => k !== "unknown")
            .map(([k, c]) => (
              <span key={k} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: c }} /> {k}
              </span>
            ))}
        </div>
      </div>
      <svg viewBox="0 0 640 380" className="w-full h-auto">
        <rect x="0" y="0" width="640" height="380" rx="12" fill="#0b1220" />
        {/* faint grid to suggest a map without needing real tiles */}
        {Array.from({ length: 8 }).map((_, i) => (
          <line key={`v${i}`} x1={i * 80} y1="0" x2={i * 80} y2="380" stroke="#152238" strokeWidth="1" />
        ))}
        {Array.from({ length: 5 }).map((_, i) => (
          <line key={`h${i}`} x1="0" y1={i * 80} x2="640" y2={i * 80} stroke="#152238" strokeWidth="1" />
        ))}

        {projected.map((zone) => {
          const severity = worstSeverity(zone.id, domains, live);
          const color = SEVERITY_COLOR[severity];
          return (
            <g
              key={zone.id}
              transform={`translate(${zone.x}, ${zone.y})`}
              className="cursor-pointer"
              onClick={() => onSelectZone?.(zone.id)}
            >
              <circle r="16" fill={color} opacity="0.18" />
              <circle r="7" fill={color} stroke="#0b1220" strokeWidth="2" />
              <text y="-22" textAnchor="middle" fontSize="12" fill="#cbd5e1" fontFamily="Inter, sans-serif">
                {zone.name}
              </text>
              <text y="34" textAnchor="middle" fontSize="10" fill="#7d8aa8">
                pop. {zone.population.toLocaleString()}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
