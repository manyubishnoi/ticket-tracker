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
  listMembers: (workspaceId: number) => request(`/workspaces/${workspaceId}/members`),
  listTickets: (
    workspaceId: number,
    opts: {
      assigneeId?: number;
      priority?: string;
      sortBy?: "created_at" | "updated_at";
      order?: "asc" | "desc";
    } = {}
  ) => {
    const params = new URLSearchParams();
    if (opts.assigneeId !== undefined) params.set("assignee_id", String(opts.assigneeId));
    if (opts.priority) params.set("priority", opts.priority);
    if (opts.sortBy) params.set("sort_by", opts.sortBy);
    if (opts.order) params.set("order", opts.order);
    const qs = params.toString();
    return request(`/workspaces/${workspaceId}/tickets${qs ? `?${qs}` : ""}`);
  },
  getTicket: (ticketId: number) => request(`/tickets/${ticketId}`),
  search: (q: string) => request(`/tickets/search?q=${q}`),
  listComments: (ticketId: number) => request(`/tickets/${ticketId}/comments`),
  addComment: (ticketId: number, body: string) =>
    request(`/tickets/${ticketId}/comments`, { method: "POST", body: JSON.stringify({ body }) }),
};
