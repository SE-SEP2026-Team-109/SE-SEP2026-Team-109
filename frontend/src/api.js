// Central API client for the MentorConnect Flask backend.
//
// Every call to the backend goes through `request()` so that:
//  - the base URL is configured in one place (VITE_API_BASE, default "/api", which the
//    Vite dev server proxies to Flask on http://127.0.0.1:5000 - see vite.config.js),
//  - the JWT is attached automatically as "Authorization: Bearer <token>",
//  - errors always become an `ApiError` with a readable message and the HTTP status,
//  - an expired/invalid token (401) signs the user out once, everywhere.
//
// Started from Abhinava's FastAPI client (Development branch); the original exported
// function names (apiLogin, apiMe, apiRegister, apiGetProfile, apiUpdateProfile) are kept.

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const TOKEN_KEY = 'mentorconnect_token'

export class ApiError extends Error {
  constructor(message, status, details) { super(message); this.status = status; this.details = details }
}

export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY) } catch (e) { return null } }
export const setToken = t => { try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY) } catch (e) { /* storage unavailable */ } }

let onUnauthorized = () => {}
export const setUnauthorizedHandler = fn => { onUnauthorized = fn }

export async function request(method, path, body) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  let res
  try {
    res = await fetch(API_BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
  } catch (e) {
    throw new ApiError('Cannot reach the MentorConnect server. Is the backend running?', 0)
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const message = data?.error?.message || data?.detail || `Request failed (${res.status})`
    if (res.status === 401 && token) onUnauthorized(message)
    throw new ApiError(message, res.status, data?.error?.details)
  }
  return data
}

export const api = {
  get: path => request('GET', path),
  post: (path, body = {}) => request('POST', path, body),
  put: (path, body = {}) => request('PUT', path, body),
  patch: (path, body = {}) => request('PATCH', path, body)
}

// ---- C1 Auth ----
export const apiRegister = payload => api.post('/auth/register', payload)
export const apiLogin = (email, password) => api.post('/auth/login', { email, password })
export const apiMe = () => api.get('/auth/me')
export const apiChangePassword = (current_password, new_password) => api.post('/auth/change-password', { current_password, new_password })
// ---- C2 Profile ----
export const apiGetProfile = () => api.get('/profile/me')
export const apiUpdateProfile = updates => api.put('/profile/me', updates)
export const apiSetMyTags = names => api.put('/profile/me/tags', { names })
// ---- C3 Tags ----
export const apiTags = () => api.get('/tags')
export const apiAdminTags = () => api.get('/admin/tags')
export const apiSuggestTag = name => api.post('/tags/suggest', { name })
export const apiAdminCreateTag = name => api.post('/admin/tags', { name })
export const apiAdminUpdateTag = (id, body) => api.patch(`/admin/tags/${id}`, body)
// ---- C4 Directory ----
export const apiMentors = (params = {}) => api.get('/mentors?' + new URLSearchParams({ page_size: 100, ...params }))
// ---- C5 Requests ----
export const apiRequests = () => api.get('/requests')
export const apiCreateRequest = (mentor_id, student_message, student_id) => api.post('/requests', { mentor_id: Number(mentor_id), student_message, ...(student_id ? { student_id: Number(student_id) } : {}) })
export const apiWithdraw = id => api.post(`/requests/${id}/withdraw`)
export const apiDecide = (id, action, reason) => api.post(`/requests/${id}/decision`, { action, reason: reason || null })
// ---- C6 Mentoring ----
export const apiMentoring = () => api.get('/mentoring')
// ---- C13 Notifications ----
export const apiNotifications = () => api.get('/notifications')
export const apiMarkRead = id => api.patch(`/notifications/${id}/read`)
export const apiMarkAllRead = () => api.patch('/notifications/read-all')
// ---- Admin ----
export const apiAdminUsers = () => api.get('/admin/users')
export const apiVerifyMentor = (id, status = 'verified') => api.patch(`/admin/mentors/${id}/verification`, { status })
