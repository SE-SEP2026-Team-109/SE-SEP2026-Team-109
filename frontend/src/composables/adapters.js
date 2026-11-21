// Adapters: translate backend JSON (snake_case, numeric ids, ISO dates, enum values) into the
// object shapes the existing pages already use (camelCase, string ids, millisecond timestamps,
// UI labels). Keeping all translation here means the pages did not have to change.
import { DEGREE_BY_COURSE, PROGRAMME_BY_COURSE_LEVEL, EMPLOYMENT_BY_STUDENT_TYPE } from '../utils/helpers'

const ms = iso => (iso ? Date.parse(iso) : null)
export const sid = v => (v === null || v === undefined ? v : String(v)) // ids are strings in the UI (route params are strings)

export function toUser(d) {
  const u = {
    id: sid(d.id), role: d.role, name: d.name || d.username || 'Unnamed user', username: d.username || '',
    email: d.email || '', phone: d.phone || '', photo: d.photo || '', status: d.status,
    active: d.status === 'active', deletionRequestedAt: d.status === 'to_be_deleted' ? ms(d.delete_time) || Date.now() : undefined,
    tags: (d.tags || []).map(t => t.name)
  }
  if (d.student) {
    const s = d.student
    Object.assign(u, {
      programme: s.courselevel ? (PROGRAMME_BY_COURSE_LEVEL[s.courselevel] || '') : 'Foundation',
      degree: DEGREE_BY_COURSE[s.course] || '', employment: EMPLOYMENT_BY_STUDENT_TYPE[s.type] || '',
      rollNo: s.rollno || '', needs: s.mneeds || '', careergoal: s.careergoal || '',
      interests: u.tags, skills: (s.skills || []).map(k => ({ name: k.name, level: k.level || 1, want: !!k.want }))
    })
  } else if (d.role === 'student') Object.assign(u, { programme: '', interests: [], needs: '', skills: [] })
  if (d.mentor) {
    const m = d.mentor
    Object.assign(u, {
      title: m.designation || '', company: m.company || '', years: m.experience || 0, industry: m.industry || '',
      careerArea: m.career_area || '', bio: m.bio || '', expertise: u.tags, support: m.support_types || [],
      capacity: m.capacity, paused: !!m.pause, verified: m.veri_status === 'verified', verification: m.veri_status,
      completed: PROGRAMME_BY_COURSE_LEVEL[m.level_completed] || '', gradYear: m.year_completed, linkedin: m.linkedin || '',
      activeCount: m.active_mentees
    })
  } else if (d.role === 'mentor') Object.assign(u, { title: '', company: '', years: 0, industry: '', bio: '', expertise: [], support: [], capacity: 0, paused: false, verified: false })
  return u
}

export const toHistory = h => ({ from: h.from, to: h.to, actor: h.actor, at: ms(h.at) })

export const toRequest = d => ({
  id: sid(d.id), studentId: sid(d.sid), mentorId: sid(d.mid), status: d.status,
  message: d.student_message || '', reason: d.mentor_response || '',
  createdAt: ms(d.created_on), expiresAt: ms(d.expires_on), source: d.req_source,
  history: (d.history || []).map(toHistory)
})

export const toMentorship = d => ({
  id: sid(d.id), studentId: sid(d.sid), mentorId: sid(d.mid), active: d.status === 'active', since: ms(d.start),
  end: ms(d.end), by: d.assigned_by ? 'Coordinator' : 'Mentor',
  studentEndRequestedAt: ms(d.student_end_requested_at), mentorEndRequestedAt: ms(d.mentor_end_requested_at)
})

export const toNotification = (d, userId) => ({ id: sid(d.id), userId, text: d.message, link: d.link, read: !!d.read, at: ms(d.created_at) })

export const toTag = d => ({ id: sid(d.id), name: d.name, type: d.type, status: d.approved === false ? 'suggested' : 'approved' })
