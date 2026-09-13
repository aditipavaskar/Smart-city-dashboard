function severityFor(value, metaCfg) {
  if (value == null || !metaCfg) return "ok";
  const { higher_is_worse, warn, critical } = metaCfg;
  const bad = higher_is_worse ? value >= critical : value <= critical;
  const warning = higher_is_worse ? value >= warn : value <= warn;
  if (bad) return "critical";
  if (warning) return "warning";
  return "ok";
}

export default function StatCard({ label, value, unit, metaCfg, onClick, selected }) {
  const severity = severityFor(value, metaCfg);
  const badgeClass = { ok: "badge-ok", warning: "badge-warning", critical: "badge-critical" }[severity];

  return (
    <button
      onClick={onClick}
      className={`card text-left w-full transition-colors ${
        selected ? "border-accent" : "hover:border-slate-500"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wide text-slate-400">{label.replace(/_/g, " ")}</span>
        <span className={`badge ${badgeClass}`}>{severity}</span>
      </div>
      <div className="text-2xl font-semibold font-mono">
        {value != null ? value.toFixed(1) : "—"} <span className="text-sm text-slate-400">{unit}</span>
      </div>
    </button>
  );
}
