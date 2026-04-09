/**
 * plugins/index.js
 *
 * Automatically included in `./src/main.js`
 */

// Plugins
import vuetify from './vuetify'
import router from '../router'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

export function registerPlugins(app) {
  const pinia = createPinia()
  pinia.use(piniaPluginPersistedstate)

  app.use(pinia).use(vuetify).use(router)
}
