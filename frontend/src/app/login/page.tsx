"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, saveToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleLogin() {
    try {
      const res = await api.login(email, password);
      saveToken(res.access_token);
      router.push("/tickets");
    } catch {
      setError("Login failed");
    }
  }

  return (
    <main>
      <h1>Log in</h1>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 320 }}>
        <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button onClick={handleLogin}>Log in</button>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
      </div>
    </main>
  );
}
