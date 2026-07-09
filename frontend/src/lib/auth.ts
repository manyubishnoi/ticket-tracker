import { getToken } from "./api";

// Decode the JWT payload on the client to read claims like is_admin.
function decodePayload(token: string): Record<string, any> | null {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export function isAdmin(): boolean {
  const token = getToken();
  if (!token) return false;
  const claims = decodePayload(token);
  return Boolean(claims?.is_admin);
}

export function currentUserEmail(): string | null {
  const token = getToken();
  if (!token) return null;
  return decodePayload(token)?.email ?? null;
}
