import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'
import Login from '@/views/Login.vue'
import Dashboard from '@/views/Dashboard.vue'
import RoleManage from '@/views/RoleManage.vue'
import UserManage from '@/views/UserManage.vue'
import ModelManage from '@/views/ModelManage.vue'

const routes = [
  { path: '/login', name: 'Login', component: Login },
  {
    path: '/',
    name: 'Layout',
    component: Layout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: Dashboard, meta: { roles: ['管理员', '编辑员'] } },
      { path: 'roles', name: 'Roles', component: RoleManage, meta: { roles: ['管理员'] } },
      { path: 'users', name: 'Users', component: UserManage, meta: { roles: ['管理员'] } },
      { path: 'models', name: 'Models', component: ModelManage, meta: { roles: ['管理员'] } },
      { path: 'knowledge-bases', name: 'KnowledgeBases', component: () => import('@/views/KbManage.vue'), meta: { roles: ['管理员', '编辑员'] } },
      { path: 'hit-test', name: 'HitTest', component: () => import('@/views/HitTest.vue'), meta: { roles: ['管理员', '编辑员'] } },
      { path: 'chat', name: 'Chat', component: () => import('@/views/ChatDialog.vue'), meta: { roles: ['管理员', '编辑员', '普通用户'] } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
    return
  }

  if (to.path !== '/login' && to.meta.roles) {
    const userInfoStr = localStorage.getItem('userInfo')
    const userInfo = userInfoStr ? JSON.parse(userInfoStr) : null
    const userRole = userInfo?.role_name
    if (!userRole || !to.meta.roles.includes(userRole)) {
      next('/chat')
      return
    }
  }

  next()
})

export default router