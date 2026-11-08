import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import './styles/tokens.css'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

// PWA Service Worker（子路径部署时 scope 自动限定在 base 下）
if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
  const swUrl = (import.meta.env.BASE_URL || '/') + 'sw.js'
  navigator.serviceWorker.register(swUrl).catch(() => {})
}
