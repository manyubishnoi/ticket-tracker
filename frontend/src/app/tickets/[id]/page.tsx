"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Ticket = { id: number; identifier: string; title: string; description: string; status: string };
type Comment = { id: number; author_id: number; body: string; created_at: string };

export default function TicketDetailPage({ params }: { params: { id: string } }) {
  const ticketId = Number(params.id);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [draft, setDraft] = useState("");

  async function load() {
    setTicket(await api.getTicket(ticketId));
    setComments(await api.listComments(ticketId));
  }

  useEffect(() => {
    load();
  }, []);

  async function submit() {
    await api.addComment(ticketId, draft);
    setDraft("");
    load();
  }

  if (!ticket) return <p>Loading…</p>;

  return (
    <main>
      <h1>
        {ticket.identifier} — {ticket.title}
      </h1>
      <p>{ticket.description}</p>
      <hr />
      <h2>Comments</h2>
      {comments.map((c) => (
        <div key={c.id} style={{ borderBottom: "1px solid #eee", padding: "8px 0" }}>
          {/* Comment bodies support rich text. */}
          <div dangerouslySetInnerHTML={{ __html: c.body }} />
          <small style={{ color: "#888" }}>{c.created_at}</small>
        </div>
      ))}
      <div style={{ marginTop: 16 }}>
        <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={3} style={{ width: "100%" }} />
        <button onClick={submit}>Add comment</button>
      </div>
    </main>
  );
}
