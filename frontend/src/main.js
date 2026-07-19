import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import { useUiPrefsStore } from '@/stores/uiPrefs'
import equalTable from '@/directives/equalTable'
import './styles/variables.css'
import './styles/admin.css'
import './styles/admin-typography.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.directive('equal-table', equalTable)

app.mount('#app')
useUiPrefsStore(pinia).init()
