import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/styles.css'
import './assets/workspace.css'
import './assets/theme.css'
import { initSession } from './composables/useStore'
// Restore a saved login (JWT) before the first page renders, so a refresh keeps you signed in.
initSession().finally(() => createApp(App).use(router).mount('#app'))
