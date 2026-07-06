const BASE = "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, detail) {
    const message =
      typeof detail === "string" ? detail : detail?.message || "Request failed";
    super(message);
    this.status = status;
    this.code = typeof detail === "object" ? detail?.code : undefined;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(0, { code: "network", message: "Can't reach the server." });
  }
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body?.detail ?? body);
  return body;
}

export const api = {
  listCampaigns: () => request("/api/campaigns"),
  getCampaign: (id) => request(`/api/campaigns/${id}`),
  createCampaign: (data) =>
    request("/api/campaigns", { method: "POST", body: JSON.stringify(data) }),
  updateCampaign: (id, data) =>
    request(`/api/campaigns/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  transition: (id, action, version) =>
    request(`/api/campaigns/${id}/transitions`, {
      method: "POST",
      body: JSON.stringify({ action, version }),
    }),
  publicView: (token) => request(`/api/public/campaigns/${token}`),
  enroll: (token, identity) =>
    request(`/api/public/campaigns/${token}/enroll`, {
      method: "POST",
      body: JSON.stringify({ identity }),
    }),
};
