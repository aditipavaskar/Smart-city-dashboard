import { useEffect, useState } from "react";
import { api } from "./api";
import { useCityStream } from "./useCityStream";
import RoleLogin from "./components/RoleLogin";
import Sidebar from "./components/Sidebar";
import CityMapView from "./components/CityMapView";
import DomainPanel from "./components/DomainPanel";
import AlertsFeed from "./components/AlertsFeed";

export default function App() {
  const [session, setSession] = useState(null); // { token, role, label, domains }
  const [allDomains, setAllDomains] = useState([]);
  const [zones, setZones] = useState([]);
  const [active, setActive] = useState("overview");

  const { latest, alerts, status } = useCityStream(session?.token);

  useEffect(() => {
    api.domains().then(setAllDomains).catch(() => {});
    api.zones().then(setZones).catch(() => {});
  }, []);

  if (!session) {
    return <RoleLogin onLogin={setSession} />;
  }

  const myDomains = allDomains.filter((d) => session.domains.includes(d.id));

  return (
    <div className="min-h-screen flex">
      <Sidebar
        session={session}
        domains={myDomains}
        active={active}
        onSelect={setActive}
        onLogout={() => setSession(null)}
        streamStatus={status}
      />

      <main className="flex-1 p-6 overflow-y-auto">
        {active === "overview" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-1">City Overview</h2>
              <p className="text-sm text-slate-400">
                Zone status reflects the worst live severity across every domain your role can see.
              </p>
            </div>
            <CityMapView
              zones={zones}
              domains={myDomains}
              live={latest}
              onSelectZone={() => {}}
            />
            <div className="grid sm:grid-cols-2 gap-4">
              {myDomains.map((d) => (
                <button
                  key={d.id}
                  onClick={() => setActive(d.id)}
                  className="card text-left hover:border-accent transition-colors"
                >
                  <div className="font-semibold">{d.label}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    {Object.keys(d.metrics).length} live metrics across {zones.length} zones
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {myDomains
          .filter((d) => d.id === active)
          .map((d) => (
            <DomainPanel
              key={d.id}
              domainId={d.id}
              domainMeta={d}
              zones={zones}
              session={session}
              live={latest[d.id]}
            />
          ))}

        {active === "alerts" && <AlertsFeed session={session} liveAlerts={alerts} />}
      </main>
    </div>
  );
}
