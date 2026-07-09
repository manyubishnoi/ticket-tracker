const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function saveToken(token: string) {
  localStorage.setItem("access_token", token);
}

export function getToken(): string | null {
  return localStorage.getItem("access_token");
}

export function clearToken() {
  localStorage.removeItem("access_token");
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request("/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  listWorkspaces: () => request("/workspaces"),
  listTickets: (workspaceId: number) => request(`/workspaces/${workspaceId}/tickets`),
  getTicket: (ticketId: number) => request(`/tickets/${ticketId}`),
  search: (q: string) => request(`/tickets/search?q=${q}`),
  listComments: (ticketId: number) => request(`/tickets/${ticketId}/comments`),
  addComment: (ticketId: number, body: string) =>
    request(`/tickets/${ticketId}/comments`, { method: "POST", body: JSON.stringify({ body }) }),
};
