export const emailOk = e => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e.trim())
// Student rule (Milestone 1, US-01): email must end with study.iitm.ac.in (ds., es., etc.)
export const iitmOk = e => /@([\w-]+\.)*study\.iitm\.ac\.in$/i.test(e.trim())
export const passOk = p => p.length >= 8 && /[A-Za-z]/.test(p) && /\d/.test(p)
export const fmt = t => new Date(t).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
export const home = role => `/${role}/dashboard`
export const list = s => [...new Set(s.split(',').map(x => x.trim()).filter(Boolean))]
export const greeting = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening' }
export const DEGREES = ['ES', 'DS', 'Aero', 'Management']
export const CAREER_AREAS = ['Data Science', 'Software Engineering', 'Product Management', 'Research', 'Analytics', 'Entrepreneurship', 'Finance']
// Maps the registration form's UI labels to the backend's Course/CourseLevel/StudentType enum values.
export const COURSE_BY_DEGREE = { ES: 'electronic_systems', DS: 'data_science_and_applications', Aero: 'aeronautics_and_space_technology', Management: 'management_and_data_science' }
export const COURSE_LEVEL_BY_PROGRAMME = { Foundation: null, Diploma: 'diploma', BSc: 'bsc_degree', 'BS Degree': 'bs_degree' }
export const STUDENT_TYPE_BY_EMPLOYMENT = { 'Studying only': 'standalone', 'Working full time': 'full_time_working_professional', 'Working part time': 'part_time_working_professional', 'Between jobs': 'standalone' }
// Reverse lookups used to render backend enum values back onto the UI's labels.
export const DEGREE_BY_COURSE = Object.fromEntries(Object.entries(COURSE_BY_DEGREE).map(([k, v]) => [v, k]))
export const PROGRAMME_BY_COURSE_LEVEL = Object.fromEntries(Object.entries(COURSE_LEVEL_BY_PROGRAMME).filter(([, v]) => v).map(([k, v]) => [v, k]))
export const EMPLOYMENT_BY_STUDENT_TYPE = Object.fromEntries(Object.entries(STUDENT_TYPE_BY_EMPLOYMENT).map(([k, v]) => [v, k]))
// Shrinks a chosen photo to a small JPEG data URL so it is cheap to keep in the browser (mock) store.
export const resizeImage = (file, max = 200) => new Promise((resolve, reject) => {
  if (!/^image\/(png|jpe?g|webp)$/.test(file.type)) return reject(new Error('Choose a PNG, JPG or WebP image.'))
  if (file.size > 5e6) return reject(new Error('The image must be smaller than 5 MB.'))
  const rd = new FileReader()
  rd.onload = () => { const img = new Image(); img.onload = () => { const k = Math.min(1, max / Math.max(img.width, img.height)), c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k); c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); resolve(c.toDataURL('image/jpeg', 0.8)) }; img.onerror = () => reject(new Error('That file is not a readable image.')); img.src = rd.result }
  rd.readAsDataURL(file)
})
