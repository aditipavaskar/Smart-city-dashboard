const DOMAIN_ICONS = {
  traffic: "🚦",
  energy: "⚡",
  pollution: "🌫️",
  public_services: "🛠️",
};

export default function Sidebar({ session, domains, active, onSelect, onLogout, streamStatus }) {
  return (
    <aside className="w-60 shrink-0 border-r border-border bg-panel/60 flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="text-accent text-xs font-mono tracking-widest">SMART CITY OPS</div>
        <div className="text-sm text-slate-400 mt-1">{session.label}</div>
      </div>

      <nav className="flex-1 p-2 space-y-1">
        <button
          onClick={() => onSelect("overview")}
          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
            active === "overview" ? "bg-accent/15 text-accent" : "hover:bg-panelAlt text-slate-300"
          }`}
        >
          🗺️ City Overview
        </button>
        {domains.map((d) => (
          <button
            key={d.id}
            onClick={() => onSelect(d.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
              active === d.id ? "bg-accent/15 text-accent" : "hover:bg-panelAlt text-slate-300"
            }`}
          >
            {DOMAIN_ICONS[d.id] || "📊"} {d.label}
          </button>
        ))}
        <button
          onClick={() => onSelect("alerts")}
          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
            active === "alerts" ? "bg-accent/15 text-accent" : "hover:bg-panelAlt text-slate-300"
          }`}
        >
          🔔 Alerts
        </button>
      </nav>

      <div className="p-4 border-t border-border text-xs text-slate-400">
        <div className="flex items-center gap-2 mb-3">
          <span
            className={`w-2 h-2 rounded-full ${
              streamStatus === "open" ? "bg-good" : streamStatus === "connecting" ? "bg-warn" : "bg-critical"
            }`}
          />
          stream {streamStatus}
        </div>
        <button onClick={onLogout} className="text-slate-400 hover:text-slate-200 underline">
          Switch role
        </button>
      </div>
    </aside>
  );
}
