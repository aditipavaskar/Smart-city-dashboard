import { useEffect, useState } from "react";
import { api } from "../api";

export default function RoleLogin({ onLogin }) {
  const [roles, setRoles] = useState([]);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(null);

  useEffect(() => {
    api.roles().then(setRoles).catch((e) => setError(e.message));
  }, []);

  async function choose(roleId) {
    setPending(roleId);
    setError(null);
    try {
      const session = await api.login(roleId);
      onLogin(session);
    } catch (e) {
      setError(e.message);
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <div className="text-accent text-sm font-mono tracking-widest mb-2">SMART CITY OPS</div>
          <h1 className="text-3xl font-bold">Choose your role to sign in</h1>
          <p className="text-slate-400 mt-2">
            Each role sees only the operational domains it owns — this is a live demo of role-based
            dashboards, not a real login.
          </p>
        </div>

        {error && (
          <div className="card border-critical/50 mb-4 text-critical text-sm">
            Couldn&apos;t reach the API at startup — is the backend running? ({error})
          </div>
        )}

        <div className="grid sm:grid-cols-2 gap-3">
          {roles.map((r) => (
            <button
              key={r.id}
              onClick={() => choose(r.id)}
              disabled={pending !== null}
              className="card text-left hover:border-accent transition-colors disabled:opacity-50"
            >
              <div className="font-semibold text-slate-100">{r.label}</div>
              <div className="text-sm text-slate-400 mt-1">{r.description}</div>
              <div className="mt-3 flex flex-wrap gap-1">
                {r.domains.map((d) => (
                  <span key={d} className="badge bg-panelAlt border border-border text-slate-300">
                    {d.replace("_", " ")}
                  </span>
                ))}
              </div>
              {pending === r.id && <div className="text-xs text-accent mt-2">Signing in…</div>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
