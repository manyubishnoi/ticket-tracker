"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { isAdmin } from "@/lib/auth";

type Ticket = {
  id: number;
  identifier: string;
  title: string;
  status: string;
  priority: string;
  assignee_id: number | null;
};

type Member = {
  id: number;
  name: string;
  email: string;
  role: string;
};

const PRIORITIES = ["none", "low", "medium", "high", "urgent"];

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [admin, setAdmin] = useState(false);
  const [workspaceId, setWorkspaceId] = useState<number | null>(null);

  const [assigneeId, setAssigneeId] = useState<string>("");
  const [priority, setPriority] = useState<string>("");
  const [sortBy, setSortBy] = useState<"created_at" | "updated_at">("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("asc");

  useEffect(() => {
    setAdmin(isAdmin());
    (async () => {
      const workspaces = await api.listWorkspaces();
      if (workspaces.length > 0) {
        setWorkspaceId(workspaces[0].id);
        setMembers(await api.listMembers(workspaces[0].id));
      }
    })();
  }, []);

  useEffect(() => {
    if (!workspaceId) return;
    (async () => {
      setTickets(
        await api.listTickets(workspaceId, {
          assigneeId: assigneeId ? Number(assigneeId) : undefined,
          priority: priority || undefined,
          sortBy,
          order,
        })
      );
    })();
  }, [workspaceId, assigneeId, priority, sortBy, order]);

  return (
    <main>
      <h1>Tickets</h1>
      {admin && <button>Delete workspace</button>}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
          <option value="">All assignees</option>
          {members.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
        <select value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value as "created_at" | "updated_at")}>
          <option value="created_at">Sort by created date</option>
          <option value="updated_at">Sort by updated date</option>
        </select>
        <select value={order} onChange={(e) => setOrder(e.target.value as "asc" | "desc")}>
          <option value="asc">Ascending</option>
          <option value="desc">Descending</option>
        </select>
      </div>
      <ul>
        {tickets.map((t) => {
          const assignee = members.find((m) => m.id === t.assignee_id);
          return (
            <li key={t.id}>
              <Link href={`/tickets/${t.id}`}>
                {t.identifier} — {t.title}
              </Link>{" "}
              <span style={{ color: "#888" }}>
                ({t.status}, {t.priority}
                {assignee ? `, ${assignee.name}` : ""})
              </span>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
