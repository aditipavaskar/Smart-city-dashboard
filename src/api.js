const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  baseUrl: BASE_URL,

  login(role) {
    return request("/auth/login", { method: "POST", body: JSON.stringify({ role }) });
  },
  roles() {
    return request("/roles");
  },
  zones() {
    return request("/zones");
  },
  domains() {
    return request("/domains");
  },
  metricsLatest(domain, role) {
    return request(`/metrics/${domain}/latest?role=${encodeURIComponent(role)}`);
  },
  metricsHistory(domain, { role, zone, metric, limit = 40 }) {
    const qs = new URLSearchParams({ role, zone, metric, limit });
    return request(`/metrics/${domain}/history?${qs.toString()}`);
  },
  predict(domain, { role, zone, metric, horizon = 6 }) {
    const qs = new URLSearchParams({ role, zone, metric, horizon });
    return request(`/predict/${domain}?${qs.toString()}`);
  },
  alerts({ role, domain, severity, limit = 50 }) {
    const qs = new URLSearchParams({ role, limit });
    if (domain) qs.set("domain", domain);
    if (severity) qs.set("severity", severity);
    return request(`/alerts?${qs.toString()}`);
  },
};

export function wsUrl(token) {
  const httpBase = BASE_URL.replace(/\/$/, "");
  const wsBase = httpBase.replace(/^http/, "ws");
  return `${wsBase}/ws/stream?token=${encodeURIComponent(token)}`;
}
