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
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: Dashboard,
        meta: { roles: ['管理员', '编辑员'] }
      },
      {
        path: 'roles',
        name: 'Roles',
        component: RoleManage,
        meta: { roles: ['管理员'] }
      },
      {
        path: 'users',
        name: 'Users',
        component: UserManage,
        meta: { roles: ['管理员'] }
      },
      {
        path: 'models',
        name: 'Models',
        component: ModelManage,
        meta: { roles: ['管理员'] }
      },
      {
        path: 'knowledge-bases',
        name: 'KnowledgeBases',
        component: () => import('@/views/KbManage.vue'),
        meta: { roles: ['管理员', '编辑员'] }
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/DocManage.vue'),
        meta: { roles: ['管理员', '编辑员'] }
      },
      {
        path: 'hit-test',
        name: 'HitTest',
        component: () => import('@/views/HitTest.vue'),
        meta: { roles: ['管理员', '编辑员'] }
      },
      {
        path: 'chat',
        name: 'ChatDialog',
        component: () => import('@/views/ChatDialog.vue'),
        meta: { roles: ['管理员', '编辑员', '普通用户'] }
      }
    ]
  },
  { path: '/kb', redirect: '/knowledge-bases' },
  { path: '/doc', redirect: '/documents' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

function getToken() {
  return localStorage.getItem('token') || localStorage.getItem('rag_token')
}

function getUserInfo() {
  const raw = localStorage.getItem('userInfo') || localStorage.getItem('rag_user')
  try {
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

function redirectByRole() {
  const roleName = getUserInfo()?.role_name
  if (roleName === '普通用户') return '/chat'
  if (roleName === '编辑员') return '/knowledge-bases'
  return '/dashboard'
}

router.beforeEach((to, from, next) => {
  const token = getToken()

  if (to.path === '/login') {
    if (token) {
      next(redirectByRole())
      return
    }
    next()
    return
  }

  if (!token) {
    next('/login')
    return
  }

  if (to.meta.roles) {
    const userRole = getUserInfo()?.role_name
    if (!userRole || !to.meta.roles.includes(userRole)) {
      next('/chat')
      return
    }
  }

  next()
})

export default router
