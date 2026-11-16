// Thin client for the FastAPI backend auth endpoints.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api'

async function parseError(res) {
  const body = await res.json().catch(() => ({}))
  return body.detail || `Request failed (${res.status})`
}

export async function apiRegister({ email, password, role, username, name, phone }) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, role, username: username || null, name: name || null, phone: phone || null })
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function apiLogin(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    body: new URLSearchParams({ username: email, password })
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function apiMe(token) {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}
