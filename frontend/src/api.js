const API_BASE = '/api';

// ── Token management ──────────────────────────────────────────────

let _token = localStorage.getItem('planit_token');

export function setToken(token) {
  _token = token;
  if (token) localStorage.setItem('planit_token', token);
  else localStorage.removeItem('planit_token');
}

export function getToken() {
  return _token;
}

export function clearAuth() {
  _token = null;
  localStorage.removeItem('planit_token');
  localStorage.removeItem('planit_user');
}

function authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;
  return headers;
}

// ── Auth API ──────────────────────────────────────────────────────

export async function register(email, password, displayName) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName || undefined }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Registration failed');
  }
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  return res.json();
}

export async function getMe() {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Not authenticated');
  return res.json();
}

// ── Session API ───────────────────────────────────────────────────

export async function createSession() {
  const res = await fetch(`${API_BASE}/session`, { method: 'POST', headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

export async function listSessions() {
  const res = await fetch(`${API_BASE}/sessions`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to list sessions');
  return res.json();
}

export async function sendMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error('Failed to send message');
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to get session');
  return res.json();
}

export async function getHistory(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/history`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to get history');
  return res.json();
}

export async function getPlanVersions(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/versions`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to get versions');
  return res.json();
}

export async function getConversationSummary(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/summary`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to get summary');
  return res.json();
}
