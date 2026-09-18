import axios from "axios";

// Empty baseURL = same origin (FastAPI serves the built app, or Vite proxies /api in dev).
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail;
    const message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join("; ")
      : err.code === "ECONNABORTED" ? "The server took too long to respond. It may be waking up; try again."
      : err.message || "Request failed";
    return Promise.reject(new Error(message));
  },
);

const data = (p) => p.then((r) => r.data);

export const api = {
  health: () => data(http.get("/api/health")),
  sites: () => data(http.get("/api/sites")),
  chat: (body) => data(http.post("/api/chat", body)),
  assess: (body) => data(http.post("/api/assess", body)),
  search: (q, limit = 8, scope = "claims") => data(http.get("/api/search", { params: { q, limit, scope } })),
  knowledge: (kind) => data(http.get(`/api/knowledge/${kind}`)),
  reportUrl: (id) => `${import.meta.env.VITE_API_URL || ""}/api/report/${id}`,
};
