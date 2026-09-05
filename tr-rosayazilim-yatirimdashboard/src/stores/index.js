import { defineStore } from '#q-app'
import { createPinia } from 'pinia'
import { securePiniaPersistence } from './persistence'

export default defineStore(() => {
  const pinia = createPinia()
  pinia.use(securePiniaPersistence)
  return pinia
})
