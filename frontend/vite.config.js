import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// During development the Vue app calls "/api/...". Vite forwards those calls to the
// Flask backend, so the browser sees one origin (no CORS problems) and no URL is hard-coded.
// Change the target with VITE_BACKEND_URL if Flask runs elsewhere.
const backend = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [vue()],
  server: { proxy: { '/api': { target: backend, changeOrigin: true } } },
  preview: { proxy: { '/api': { target: backend, changeOrigin: true } } }
})
