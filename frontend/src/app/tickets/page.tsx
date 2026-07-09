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
};

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [admin, setAdmin] = useState(false);

  useEffect(() => {
    setAdmin(isAdmin());
    (async () => {
      const workspaces = await api.listWorkspaces();
      if (workspaces.length > 0) {
        setTickets(await api.listTickets(workspaces[0].id));
      }
    })();
  }, []);

  return (
    <main>
      <h1>Tickets</h1>
      {admin && <button>Delete workspace</button>}
      <ul>
        {tickets.map((t) => (
          <li key={t.id}>
            <Link href={`/tickets/${t.id}`}>
              {t.identifier} — {t.title}
            </Link>{" "}
            <span style={{ color: "#888" }}>({t.status}, {t.priority})</span>
          </li>
        ))}
      </ul>
    </main>
  );
}
