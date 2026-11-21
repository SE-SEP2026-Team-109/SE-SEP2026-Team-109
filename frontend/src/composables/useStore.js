import { reactive, watch } from 'vue'
import { seed } from '../data/mock'
import {
  ApiError, getToken, setToken, setUnauthorizedHandler, apiLogin, apiMe, apiRegister, apiUpdateProfile, apiSetMyTags,
  apiChangePassword, apiTags, apiAdminTags, apiSuggestTag, apiAdminCreateTag, apiAdminUpdateTag, apiMentors, apiRequests,
  apiCreateRequest, apiWithdraw, apiDecide, apiMentoring, apiNotifications, apiMarkRead, apiMarkAllRead, apiAdminUsers,
  apiVerifyMentor
} from '../api'
import { toUser, toRequest, toMentorship, toNotification, toTag } from './adapters'
import { COURSE_BY_DEGREE, COURSE_LEVEL_BY_PROGRAMME, STUDENT_TYPE_BY_EMPLOYMENT } from '../utils/helpers'

/* ============================================================================
   HOW DATA WORKS NOW (Sprint 1 integration)
   - Users, profiles, tags, mentor directory, requests, mentorships and notifications come
     from the Flask API and are saved in the SQLite database. `state` is only an in-memory
     copy (cache) of what the server returned, refreshed after every change.
   - Features whose APIs are Sprint 2 (goals, availability, sessions, action items, feedback,
     reports, coordinator groups, to-dos) still work in the browser only. Their data is kept in
     localStorage under LOCAL_KEY so it survives a refresh. See docs/frontend-integration.md.
   ============================================================================ */
const LOCAL_KEY = 'mentorconnect_local_v1'
const LOCAL_SLICES = ['goals', 'availability', 'sessions', 'feedback', 'platformFeedback', 'reports', 'groups', 'messages', 'audit', 'criteria', 'todos']
const SERVER_SLICES = { users: [], requests: [], mentorships: [], notifications: [], tags: [] }
function emptyLocal() {
  const s = seed()
  // Sprint 2 data starts empty for real accounts (the old mock rows pointed at mock-only users).
  return { goals: [], availability: [], sessions: [], feedback: [], platformFeedback: [], reports: [], groups: {}, messages: [], audit: [], criteria: s.criteria, todos: {} }
}
function load() {
  let local = emptyLocal()
  try { const saved = JSON.parse(localStorage.getItem(LOCAL_KEY)); if (saved && typeof saved === 'object') local = { ...local, ...saved } } catch (e) { /* ignore corrupt data */ }
  return { sessionId: null, ready: false, loading: false, ...structuredClone(SERVER_SLICES), ...local }
}
export const state = reactive(load())
watch(() => LOCAL_SLICES.map(k => state[k]), () => {
  try { localStorage.setItem(LOCAL_KEY, JSON.stringify(Object.fromEntries(LOCAL_SLICES.map(k => [k, state[k]])))) } catch (e) { /* storage unavailable */ }
}, { deep: true })
export const resetDemo = () => { try { localStorage.removeItem(LOCAL_KEY) } catch (e) { /* ignore */ } location.href = location.pathname }

export const toasts = reactive([])
export function toast(msg, type = 'ok') { const t = { id: Math.random(), msg, type }; toasts.push(t); setTimeout(() => toasts.splice(toasts.indexOf(t), 1), 3500) }

export const DAY = 864e5, MAX_PENDING = 3, EXPIRY_DAYS = 14, RETENTION_DAYS = 30, EDIT_WINDOW = 15 * 60 * 1000
const uid = p => p + Math.random().toString(36).slice(2, 8)
export const me = () => state.users.find(u => u.id === state.sessionId)
export const userById = id => state.users.find(u => u.id === id) || { id, name: 'Unknown user', role: '', email: '' }
export const live = u => u.active !== false && !u.purged
// A mentor is visible to students only when profile is complete, admin-verified and the account is live.
export const mentors = () => state.users.filter(u => u.role === 'mentor' && u.title && u.verified && live(u))
export const activeMentees = id => state.mentorships.filter(m => m.mentorId === id && m.active)
// The server tells us how many mentees each mentor has (students cannot see other students' mentorships).
export const activeCount = m => (m.activeCount ?? activeMentees(m.id).length)
export const openSlots = m => (m.paused ? 0 : Math.max(0, m.capacity - activeCount(m)))
export const pendingOf = sid => state.requests.filter(r => r.studentId === sid && r.status === 'pending')
// Local-only notification (used by Sprint 2 browser-only features). Server notifications replace these on refresh.
export const notify = (userId, text, link) => state.notifications.unshift({ id: uid('n'), userId, text, link, read: false, at: Date.now(), local: true })
const log = (actor, text) => state.audit.unshift({ id: uid('au'), at: Date.now(), actor: typeof actor === 'string' ? actor : actor.name, text })
export const myMentorships = uidv => state.mentorships.filter(m => m.active && (m.studentId === uidv || m.mentorId === uidv))
export const mentorshipOf = (a, b) => state.mentorships.find(m => m.active && ((m.studentId === a && m.mentorId === b) || (m.studentId === b && m.mentorId === a)))
export const aliasOf = id => 'Student #' + (state.users.filter(u => u.role === 'student').findIndex(u => u.id === id) + 1)
export const relayEmail = id => 'student-' + [...id].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 9973, 7).toString(36) + '@relay.mentorconnect.demo'
export const fmtDT = t => new Date(t).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
const errText = e => (e instanceof ApiError ? e.message : (e && e.message) || 'Something went wrong. Please try again.')

/* ---------- loading data from the server ---------- */
// Insert or update a user in the cache. A user's own record is never replaced by a less complete copy.
function upsertUser(dto) {
  if (!dto) return null
  const fresh = toUser(dto)
  const i = state.users.findIndex(u => u.id === fresh.id)
  if (i < 0) { state.users.push(fresh); return fresh }
  const old = state.users[i]
  if (old.id === state.sessionId && !fresh.email) return old
  Object.assign(old, fresh)
  return old
}
async function loadRequests() {
  const list = await apiRequests()
  list.forEach(r => { upsertUser(r.student); upsertUser(r.mentor) })
  state.requests = list.map(toRequest)
}
async function loadMentorships() {
  const list = await apiMentoring()
  list.forEach(m => { upsertUser(m.student); upsertUser(m.mentor) })
  state.mentorships = list.map(toMentorship)
}
async function loadNotifications() {
  const id = state.sessionId
  state.notifications = (await apiNotifications()).map(n => toNotification(n, id))
}
async function loadTags(admin) { state.tags = (await (admin ? apiAdminTags() : apiTags())).map(toTag) }
async function loadMe() { const u = upsertUser(await apiMe()); state.sessionId = u.id; return u }

// Loads everything the signed-in role needs. Called after login, on page refresh and after changes.
export async function refresh() {
  const u = me(); if (!u) return
  const jobs = [loadNotifications(), loadTags(u.role === 'admin'), loadMe()]
  if (u.role === 'student' || u.role === 'coordinator' || u.role === 'admin') jobs.push(apiMentors().then(r => r.items.forEach(upsertUser)))
  if (u.role === 'admin') jobs.push(apiAdminUsers().then(list => list.forEach(upsertUser)))
  jobs.push(loadRequests(), loadMentorships())
  const results = await Promise.allSettled(jobs)
  const failed = results.find(r => r.status === 'rejected')
  if (failed) toast(errText(failed.reason), 'err')
}

// Runs once when the app starts: if a saved token is still valid, restore the session.
export async function initSession() {
  setUnauthorizedHandler(message => {
    if (!state.sessionId) return
    clearServerState(); setToken(null)
    toast(message || 'Your session has expired. Please sign in again.', 'err')
    location.hash = '#/login'
  })
  if (getToken()) {
    try { await loadMe(); await refresh() } catch (e) { setToken(null); clearServerState() }
  }
  // The registration page needs the approved tag list before anyone signs in (GET /api/tags is public).
  if (!state.sessionId) { try { await loadTags(false) } catch (e) { /* page still works; tags just appear empty */ } }
  state.ready = true
}
function clearServerState() {
  const tags = state.tags.filter(t => t.status === 'approved') // public list, still useful on the login/register pages
  Object.assign(state, structuredClone(SERVER_SLICES)); state.sessionId = null; state.tags = tags
}

/* ---------- accounts (C1 Auth, C2 Profile) ---------- */
export async function login(email, password) {
  try {
    const res = await apiLogin(email.trim(), password)
    setToken(res.access_token)
    clearServerState()
    const u = upsertUser(res.user); state.sessionId = u.id
    await refresh()
    return { user: me() }
  } catch (e) { setToken(null); return { error: errText(e) } }
}
export const logout = () => { setToken(null); clearServerState() }

// Kept for pages that call it (Abhinava's API version); now simply re-reads the profile.
export async function loadProfile() { if (me()) { try { await loadMe() } catch (e) { /* keep cached copy */ } } }
// Saves profile fields, then (optionally) the tag selection. Returns an error message or null.
export async function saveProfile(body, tagNames) {
  if (!me()) return 'You must be signed in to save your profile.'
  try {
    upsertUser(await apiUpdateProfile(body))
    if (tagNames) upsertUser(await apiSetMyTags(tagNames))
    return null
  } catch (e) { return errText(e) }
}
// Mentor capacity (1-10) and pause toggle (US-04).
export async function saveMentorSettings(patch) { return saveProfile({ mentor: patch }) }

export async function register({ name, email, password, role, extra = {} }) {
  const un = (extra.username || '').trim().toLowerCase()
  if (!usernameOk(un)) return 'Choose a username of 3 to 20 lowercase letters, numbers or underscores.'
  const payload = { email: email.trim(), password, role, username: un, name: name.trim(), phone: extra.phone || null }
  if (role === 'student') {
    Object.assign(payload, {
      rollno: extra.rollNo || null, courselevel: COURSE_LEVEL_BY_PROGRAMME[extra.programme] || null,
      course: COURSE_BY_DEGREE[extra.degree] || null, student_type: STUDENT_TYPE_BY_EMPLOYMENT[extra.employment] || null
    })
  } else if (role === 'mentor') {
    Object.assign(payload, {
      designation: extra.title, company: extra.company, experience: Number(extra.years) || 0, bio: extra.bio,
      industry: extra.industry || null, career_area: extra.careerArea || null, support_types: extra.support || [],
      expertise: extra.expertise || [], capacity: Number(extra.capacity), linkedin: extra.linkedin || null,
      level_completed: COURSE_LEVEL_BY_PROGRAMME[extra.completed] || null, year_completed: extra.gradYear ? Number(extra.gradYear) : null
    })
  }
  try { await apiRegister(payload); return null } catch (e) { return errText(e) }
}

/* ---------- requests (C5) and mentorships (C6) ---------- */
// The server enforces every rule (50-1500 chars, 3 pending, capacity, one mentor...). We only show its message.
export async function submitRequest(sid, mid, message) {
  try { await apiCreateRequest(mid, message.trim()); await Promise.all([loadRequests(), apiMentors().then(r => r.items.forEach(upsertUser))]); return null } catch (e) { return errText(e) }
}
export async function withdraw(id) {
  try { await apiWithdraw(id); await loadRequests(); return null } catch (e) { return errText(e) }
}
function startMentorship(studentId, mentorId, by) {
  // Browser-only: used by coordinator matching until the C15 matching API exists (Sprint 2).
  state.mentorships.push({ id: uid('ms'), studentId, mentorId, active: true, since: Date.now(), by, local: true })
  state.goals.filter(g => g.studentId === studentId).forEach(g => { g.visibility = 'mentor' })
}
// to = 'accepted' | 'rejected'; reason is optional (US-08).
export async function decide(id, mid, to, reason = '') {
  try {
    await apiDecide(id, to === 'accepted' ? 'accept' : 'reject', reason.trim())
    if (to === 'accepted') {
      const r = state.requests.find(x => x.id === id)
      if (r) state.goals.filter(g => g.studentId === r.studentId).forEach(g => { g.visibility = 'mentor' })
    }
    await Promise.all([loadRequests(), loadMentorships(), loadMe()])
    return null
  } catch (e) { return errText(e) }
}
/* ---------- notifications (C13) ---------- */
export async function markRead(n) {
  if (n.read) return
  n.read = true
  if (!n.local) { try { await apiMarkRead(n.id) } catch (e) { n.read = false; toast(errText(e), 'err') } }
}
export async function markAllRead() {
  state.notifications.filter(n => n.userId === state.sessionId).forEach(n => { n.read = true })
  try { await apiMarkAllRead() } catch (e) { toast(errText(e), 'err'); await loadNotifications() }
}

// Request expiry (US-09) now runs on the SERVER (lazily before every request call, and via
// `flask run-jobs`). The router still calls runExpiry() on navigation; it is kept as a no-op
// hook so Sprint 2 browser-only jobs can be added back without touching the router.
export function runExpiry() { /* server-side now - see backend/app/services/jobs.py */ }
// Stuck-request reminders are a C16 Sprint 2 server job; nothing runs in the browser any more.
export function runReminders() { return 0 }
// Account purge is a C14/C16 Sprint 2 server job. Returns 0 so the admin "purge" button shows "nothing to purge".
export function runPurge() { return 0 }

/* ---------- goals ---------- */
export const VIS = [['me', 'Private (only me)'], ['all', 'All mentors (anonymous)'], ['mentor', 'Only my mentor']]
// Coordinators can see every goal that is not private.
export const coordinatorGoals = () => state.goals.filter(g => g.visibility !== 'me')
export function addGoal(sid, title, target, description = '', visibility = 'me', tags = []) {
  if (title.trim().length < 3) return 'Give the goal a title of at least 3 characters.'
  if (!target || new Date(target) < new Date(new Date().toDateString())) return 'Choose a target date that is today or later.'
  state.goals.push({ id: uid('g'), studentId: sid, title: title.trim(), description: description.trim(), target, status: 'todo', visibility, tags }); return null
}
export const openGoals = () => state.goals.filter(g => g.visibility === 'all' && g.status !== 'done')

/* ---------- availability and sessions ---------- */
const toMs = v => new Date(v).getTime()
function slotCheck(mid, s, e, selfId) {
  if (!s || !e || isNaN(s) || isNaN(e)) return 'Choose a start and end time.'
  if (e <= s) return 'The end time must be after the start time.'
  if (s < Date.now()) return 'Past time slots cannot be offered.'
  if (state.availability.some(a => a.mentorId === mid && a.id !== selfId && s < a.end && e > a.start)) return '409 Conflict: this overlaps one of your existing slots.'
  return null
}
export function addSlot(mid, start, end) { const s = toMs(start), e = toMs(end), er = slotCheck(mid, s, e); if (er) return er; state.availability.push({ id: uid('av'), mentorId: mid, start: s, end: e, status: 'open', sessionId: null }); return null }
export function updateSlot(id, mid, start, end) {
  const a = state.availability.find(x => x.id === id && x.mentorId === mid); if (!a) return 'Slot not found.'
  if (a.status !== 'open') return 'Slots with a pending request or a booking cannot be changed. Cancel or reschedule the session first.'
  const s = toMs(start), e = toMs(end), er = slotCheck(mid, s, e, id); if (er) return er; Object.assign(a, { start: s, end: e }); return null
}
export function removeSlot(id, mid) {
  const a = state.availability.find(x => x.id === id && x.mentorId === mid); if (!a) return 'Slot not found.'
  if (a.status !== 'open') return 'Slots with a pending request or a booking cannot be removed. Cancel or reschedule the session first.'
  state.availability.splice(state.availability.indexOf(a), 1); return null
}
// A student REQUESTS a slot. It stays pending until the mentor confirms it.
export function requestSession(slotId, sid) {
  const a = state.availability.find(x => x.id === slotId); if (!a) return 'Slot not found.'
  const ms = state.mentorships.find(m => m.active && m.studentId === sid && m.mentorId === a.mentorId)
  if (!ms) return 'You can only request sessions with your own mentor.'
  if (a.status !== 'open') return '409 Conflict: this slot has just been taken by someone else.'
  if (a.start < Date.now()) return 'This slot is in the past.'
  const s = { id: uid('se'), mentorshipId: ms.id, mentorId: a.mentorId, studentId: sid, slotId: a.id, start: a.start, end: a.end, status: 'requested', notes: '', items: [] }
  state.sessions.push(s); a.status = 'pending'; a.sessionId = s.id
  notify(a.mentorId, `${userById(sid).name} requested a session for ${fmtDT(a.start)}`, '/mentor/sessions'); return null
}
export function respondSession(id, mentorId, accept) {
  const s = state.sessions.find(x => x.id === id); if (!s || s.mentorId !== mentorId) return 'Session not found.'
  if (s.status !== 'requested') return 'This request has already been answered.'
  const a = state.availability.find(x => x.id === s.slotId)
  if (accept) { s.status = 'scheduled'; if (a) a.status = 'booked' } else { s.status = 'declined'; if (a) { a.status = 'open'; a.sessionId = null } }
  notify(s.studentId, accept ? `Your session on ${fmtDT(s.start)} is confirmed` : `Your session request for ${fmtDT(s.start)} was declined`, '/student/sessions'); return null
}
const part = (s, u) => s && (s.studentId === u || s.mentorId === u)
export const sessionsOf = u => state.sessions.filter(s => part(s, u)).sort((a, b) => a.start - b.start)
export function cancelSession(id, actor) {
  const s = state.sessions.find(x => x.id === id); if (!part(s, actor)) return 'Session not found.'
  if (!['requested', 'scheduled'].includes(s.status)) return 'Only upcoming sessions can be cancelled.'
  s.status = 'cancelled'; const a = state.availability.find(x => x.id === s.slotId); if (a) { a.status = 'open'; a.sessionId = null }
  const other = actor === s.studentId ? s.mentorId : s.studentId
  notify(other, `${userById(actor).name} cancelled the session on ${fmtDT(s.start)}`, actor === s.studentId ? '/mentor/sessions' : '/student/sessions'); return null
}
// Reschedule moves an upcoming session to another open slot of the same mentor. A student's change needs the mentor to confirm again; a mentor's change is confirmed straight away.
export function rescheduleSession(id, actor, newSlotId) {
  const s = state.sessions.find(x => x.id === id); if (!part(s, actor)) return 'Session not found.'
  if (!['requested', 'scheduled'].includes(s.status)) return 'Only upcoming sessions can be rescheduled.'
  if (s.start <= Date.now()) return 'This session has already started.'
  const n = state.availability.find(x => x.id === newSlotId); if (!n || n.mentorId !== s.mentorId) return 'Choose one of this mentor’s open slots.'
  if (n.status !== 'open') return '409 Conflict: this slot is no longer open.'
  if (n.start < Date.now()) return 'This slot is in the past.'
  const old = state.availability.find(x => x.id === s.slotId); if (old) { old.status = 'open'; old.sessionId = null }
  const byStudent = actor === s.studentId
  n.status = byStudent ? 'pending' : 'booked'; n.sessionId = s.id
  const was = s.start; Object.assign(s, { slotId: n.id, start: n.start, end: n.end, status: byStudent ? 'requested' : 'scheduled' })
  notify(byStudent ? s.mentorId : s.studentId, `${userById(actor).name} moved the session from ${fmtDT(was)} to ${fmtDT(n.start)}${byStudent ? '. Please confirm it.' : ''}`, byStudent ? '/mentor/sessions' : '/student/sessions'); return null
}
export function logNotes(id, actor, notes) {
  const s = state.sessions.find(x => x.id === id); if (!part(s, actor)) return 'Session not found.'
  if (s.start > Date.now()) return 'Session notes cannot be added before the session date.'
  if (s.status === 'cancelled') return 'This session was cancelled.'
  if (notes.trim().length < 10) return 'Write a short summary of at least 10 characters.'
  s.notes = notes.trim(); s.status = 'completed'; return null
}
export function logPastSession(msId, actor, date, time, notes) {
  const ms = state.mentorships.find(m => m.id === msId); if (!ms || !(ms.studentId === actor || ms.mentorId === actor)) return 'Mentorship not found.'
  const start = toMs(`${date}T${time || '10:00'}`); if (isNaN(start)) return 'Choose a date and time.'
  if (start > Date.now()) return 'Session dates cannot be in the future.'
  if (notes.trim().length < 10) return 'Write a short summary of at least 10 characters.'
  state.sessions.push({ id: uid('se'), mentorshipId: msId, mentorId: ms.mentorId, studentId: ms.studentId, slotId: null, start, end: start + 36e5, status: 'completed', notes: notes.trim(), items: [] }); return null
}
export function addItem(id, actor, text, assignee) {
  const s = state.sessions.find(x => x.id === id); if (!part(s, actor)) return 'Session not found.'
  if (s.status !== 'completed') return 'Action items can be added once the session is completed.'
  if (text.trim().length < 3) return 'Describe the action item (at least 3 characters).'
  if (!['student', 'mentor'].includes(assignee)) return 'Assign the item to the student or the mentor.'
  s.items.push({ id: uid('ai'), text: text.trim(), done: false, assignee, createdBy: actor }); return null
}
export function deleteItem(id, actor, itemId) {
  const s = state.sessions.find(x => x.id === id); if (!part(s, actor)) return 'Session not found.'
  const it = s.items.find(i => i.id === itemId); if (!it) return 'Action item not found.'
  if (!(it.createdBy === actor || it.assignee === userById(actor).role)) return 'Only the person who created or was assigned this item can delete it.'
  s.items.splice(s.items.indexOf(it), 1); return null
}
export const allItems = u => sessionsOf(u).filter(s => s.status === 'completed').flatMap(s => s.items.map(i => ({ ...i, sessionId: s.id, sessionStart: s.start, other: userById(s.studentId === u ? s.mentorId : s.studentId).name })))

/* ---------- feedback ---------- */
// Completed sessions the user has not given feedback on yet, newest first.
export const feedbackDue = u => state.sessions.filter(s => s.status === 'completed' && part(s, u) && !state.feedback.some(f => f.sessionId === s.id && f.fromId === u)).sort((a, b) => b.start - a.start)
export function giveFeedback({ fromId, mentorshipId, kind, sessionId, scores, comments, isPublic }) {
  const ms = state.mentorships.find(m => m.id === mentorshipId); if (!ms || !(ms.studentId === fromId || ms.mentorId === fromId)) return 'Mentorship not found.'
  if (!['session', 'final'].includes(kind)) return 'Choose session feedback or final feedback.'
  if (kind === 'session') {
    const ss = state.sessions.find(x => x.id === sessionId)
    if (!ss || ss.mentorshipId !== mentorshipId || ss.status !== 'completed') return 'Choose a completed session.'
    if (state.feedback.some(f => f.sessionId === sessionId && f.fromId === fromId)) return 'You already sent feedback for this session.'
  }
  if (state.criteria.some(c => !(scores[c] >= 1 && scores[c] <= 5))) return 'Rate every criterion from 1 to 5.'
  if (comments.length > 500) return 'Comments are limited to 500 characters.'
  const toId = fromId === ms.studentId ? ms.mentorId : ms.studentId
  state.feedback.push({ id: uid('f'), mentorshipId, sessionId: kind === 'session' ? sessionId : null, fromId, toId, kind, scores: { ...scores }, comments: comments.trim(), isPublic: !!isPublic && kind === 'final' && fromId === ms.studentId, createdAt: Date.now() }); return null
}
export function editFeedback(id, actor, patch) {
  const f = state.feedback.find(x => x.id === id && x.fromId === actor); if (!f) return 'Feedback not found.'
  if (Date.now() - f.createdAt > EDIT_WINDOW) return 'The 15-minute edit window has closed.'
  if (state.criteria.some(c => !(patch.scores[c] >= 1 && patch.scores[c] <= 5))) return 'Rate every criterion from 1 to 5.'
  if (patch.comments.length > 500) return 'Comments are limited to 500 characters.'
  Object.assign(f, { scores: { ...patch.scores }, comments: patch.comments.trim(), isPublic: f.kind === 'final' && userById(actor).role === 'student' ? !!patch.isPublic : false }); return null
}
export function sendPlatformFeedback(text) { if (text.trim().length < 10) return 'Write at least 10 characters.'; state.platformFeedback.unshift({ id: uid('pf'), text: text.trim(), at: Date.now() }); return null } // no author stored: anonymous
export const avgScore = f => { const v = Object.values(f.scores); return v.length ? (v.reduce((a, b) => a + b, 0) / v.length).toFixed(1) : '–' }

/* ---------- tags, criteria (C3) ---------- */
export const approvedTags = () => state.tags.filter(t => t.status === 'approved').map(t => t.name)
export async function suggestTag(name) {
  const n = name.trim(); if (n.length < 2) return 'Tag names need at least 2 characters.'
  try { const t = await apiSuggestTag(n); if (me()?.role === 'admin') state.tags.push(toTag(t)); return null } catch (e) { return errText(e) }
}
export async function addTag(name) {
  const n = name.trim(); if (n.length < 2) return 'Tag names need at least 2 characters.'
  try { await apiAdminCreateTag(n); await loadTags(true); return null } catch (e) { return errText(e) }
}
export async function approveTag(id) { try { await apiAdminUpdateTag(id, { action: 'approve' }); await loadTags(true); return null } catch (e) { return errText(e) } }
export async function rejectTag(id) { try { await apiAdminUpdateTag(id, { action: 'reject' }); await loadTags(true); return null } catch (e) { return errText(e) } }
// Browser-only until a merge API exists (open decision D-07): it changes the cached view, not the database.
export function mergeTags(fromId, toId) {
  const a = state.tags.find(t => t.id === fromId), b = state.tags.find(t => t.id === toId); if (!a || !b || a === b) return 'Choose two different tags.'
  return 'Merging tags is not connected to the server yet (planned for Sprint 2). Edit or reject the duplicate instead.'
}

/* ---------- moderation, accounts (C12/C14: Sprint 2, browser-only for now) ---------- */
function move(r, to, actor, reason = '') { r.history.push({ from: r.status, to, actor, at: Date.now() }); r.status = to; if (reason) r.reason = reason }
export function submitReport(reporterId, reportedId, category, description, evidence) {
  if (!reportedId) return 'Choose who you are reporting.'
  if (reportedId === reporterId) return 'You cannot report yourself.'
  if (!category) return 'Choose a category.'
  if (description.trim().length < 20) return 'Describe what happened in at least 20 characters.'
  state.reports.unshift({ id: uid('rp'), reporterId, reportedId, category, description: description.trim(), evidence: evidence || '', status: 'open', action: '', createdAt: Date.now() })
  state.users.filter(u => u.role === 'admin').forEach(a => notify(a.id, 'A new report needs review', '/admin/dashboard?tab=reports')); return null
}
export function setActive(userId, active, admin) {
  const u = userById(userId); u.active = active
  if (!active) state.requests.filter(r => r.status === 'pending' && (r.mentorId === u.id || r.studentId === u.id)).forEach(r => {
    move(r, 'withdrawn', 'Admin'); notify(r.studentId, 'A request was closed by an admin action', '/student/requests'); if (u.role === 'student') notify(r.mentorId, 'A pending request was closed by an admin action', '/mentor/requests')
  })
  log(admin, `${active ? 'Reactivated' : 'Blocked'} ${u.name}`)
}
// Mentor verification is saved on the server (admin only). The server also notifies the mentor.
export async function verifyMentor(id, admin) {
  try { upsertUser(await apiVerifyMentor(id, 'verified')); log(admin, `Verified mentor ${userById(id).name}`); return null } catch (e) { return errText(e) }
}
export function requestDeletion(id) {
  const u = userById(id)
  state.requests.filter(r => r.status === 'pending' && (r.studentId === id || r.mentorId === id)).forEach(r => { move(r, 'withdrawn', 'System'); notify(r.studentId === id ? r.mentorId : r.studentId, 'A pending request was closed because an account was deleted', '/notifications') })
  state.mentorships.filter(m => m.active && (m.studentId === id || m.mentorId === id)).forEach(m => { m.active = false; notify(m.studentId === id ? m.mentorId : m.studentId, 'A mentorship ended because an account was deleted', '/notifications') })
  u.deletionRequestedAt = Date.now(); u.active = false; log('System', `Deletion requested by ${u.role} ${u.name}`)
}

/* ---------- matching, coordination ---------- */
export function assignMentor(studentId, mentorId, by) {
  const m = userById(mentorId), s = userById(studentId)
  if (!m.verified || !live(m) || !m.title) return 'This mentor is not available.'
  if (m.paused) return 'This mentor has paused new requests.'
  if (activeMentees(mentorId).length >= m.capacity) return '409 Conflict: this mentor has no open place, so the assignment was blocked.'
  if (state.mentorships.some(x => x.active && x.studentId === studentId)) return 'This student already has a mentor.'
  if (mentorshipOf(studentId, mentorId)) return 'They are already matched.'
  startMentorship(studentId, mentorId, by.role); log(by, `Matched ${s.name} with ${m.name}`)
  notify(studentId, `You have been matched with ${m.name}`, '/student/dashboard'); notify(mentorId, `You have been matched with ${s.name}`, '/mentor/mentees'); return null
}
export function assignGroup(coordId, msId) { const g = state.groups[coordId] || (state.groups[coordId] = []); if (!g.includes(msId)) g.push(msId) }
export function unassignGroup(coordId, msId) { state.groups[coordId] = (state.groups[coordId] || []).filter(x => x !== msId) }
export function contactStudent(coord, studentId, text) {
  if (text.trim().length < 10) return 'Write a message of at least 10 characters.'
  state.messages.push({ id: uid('msg'), fromId: coord.id, toId: studentId, text: text.trim(), at: Date.now() })
  notify(studentId, `Message from the programme coordinator: ${text.trim().slice(0, 140)}`, '/notifications'); return null
}
export const stuckRequests = () => state.requests.filter(r => r.status === 'pending' && Date.now() - r.createdAt > 7 * DAY).map(r => ({ id: r.id, ref: 'REQ-' + r.id.slice(-3).toUpperCase(), status: r.status, ageDays: Math.floor((Date.now() - r.createdAt) / DAY), reminded: r.remindedAt || null }))
export const unmatchedStudents = () => state.users.filter(u => u.role === 'student' && live(u) && !state.mentorships.some(m => m.active && m.studentId === u.id))
export function toggleItem(sessionId, actorRole, itemId) {
  const s = state.sessions.find(x => x.id === sessionId), it = s && s.items.find(i => i.id === itemId)
  if (!it) return 'Action item not found.'
  if (it.assignee !== actorRole) return `Only the ${it.assignee} can mark this item.`
  it.done = !it.done; return null
}

/* ---------- account details ---------- */
export const usernameOk = v => /^[a-z0-9_]{3,20}$/.test(v)
export const usernameTaken = (v, exceptId) => state.users.some(u => u.id !== exceptId && (u.username || '').toLowerCase() === v.toLowerCase())
export async function setUsername(id, v) {
  const n = v.trim().toLowerCase()
  if (!usernameOk(n)) return 'Username must be 3 to 20 characters: lowercase letters, numbers or underscores.'
  return saveProfile({ username: n })
}
export async function changePassword(id, current, next) {
  if (!(next.length >= 8 && /[A-Za-z]/.test(next) && /\d/.test(next))) return 'The new password needs at least 8 characters, with letters and numbers.'
  if (next === current) return 'Choose a password that is different from the current one.'
  try { await apiChangePassword(current, next); return null } catch (e) { return errText(e) }
}
export async function setPhoto(id, dataUrl) { const err = await saveProfile({ photo: dataUrl || '' }); if (err) toast(err, 'err'); return err }
// Coordinator to-do list: browser-only (no table in the M2 design; open decision D-06).
const todosOf = id => (state.todos[id] || (state.todos[id] = []))
export const userTodos = id => state.todos[id] || []
export function addTodo(id, text) { if (text.trim().length < 2) return 'Write a short task.'; todosOf(id).push({ id: uid('t'), text: text.trim(), done: false }); return null }
export const toggleTodo = (id, tid) => { const t = todosOf(id).find(x => x.id === tid); if (t) t.done = !t.done }
export const removeTodo = (id, tid) => { state.todos[id] = todosOf(id).filter(x => x.id !== tid) }
