import Link from "next/link";

export default function Home() {
  return (
    <main>
      <h1>Ticket Tracker</h1>
      <p>A minimal Linear-style issue tracker.</p>
      <ul>
        <li><Link href="/login">Log in</Link></li>
        <li><Link href="/tickets">Tickets</Link></li>
      </ul>
    </main>
  );
}
