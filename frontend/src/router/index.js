import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'
import Login from '@/views/Login.vue'
import Dashboard from '@/views/Dashboard.vue'
import RoleManage from '@/views/RoleManage.vue'
import UserManage from '@/views/UserManage.vue'
import UserGroupManage from '@/views/UserGroupManage.vue'
import ModelManage from '@/views/ModelManage.vue'
import BrandingConfig from '@/views/BrandingConfig.vue'
import { resolveRoleCode } from '@/utils/role'
import { useChatStore } from '@/stores/chat'

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
        meta: { roles: ['admin'] }
      },
      {
        path: 'roles',
        name: 'Roles',
        component: RoleManage,
        meta: { roles: ['admin'] }
      },
      {
        path: 'users',
        name: 'Users',
        component: UserManage,
        meta: { roles: ['admin'] }
      },
      {
        path: 'user-groups',
        name: 'UserGroups',
        component: UserGroupManage,
        meta: { roles: ['admin'] }
      },
      {
        path: 'models',
        name: 'Models',
        component: ModelManage,
        meta: { roles: ['admin'] }
      },
      {
        path: 'branding',
        name: 'Branding',
        component: BrandingConfig,
        meta: { roles: ['admin', 'user'] }
      },
      {
        path: 'knowledge-bases',
        name: 'KnowledgeBases',
        component: () => import('@/views/KbManage.vue'),
        meta: { roles: ['admin'] }
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/DocManage.vue'),
        meta: { roles: ['admin'] }
      },
      {
        path: 'hit-test',
        name: 'HitTest',
        component: () => import('@/views/HitTest.vue'),
        meta: { roles: ['admin', 'user'] }
      },
      {
        path: 'chunk-strategy',
        redirect: '/knowledge-bases'
      },
      {
        path: 'model-runtime',
        name: 'ModelRuntime',
        component: () => import('@/views/ModelRuntimeConfig.vue'),
        meta: { roles: ['admin'] }
      },
      {
        path: 'eval-tasks',
        name: 'EvalTasks',
        component: () => import('@/views/EvalTaskManage.vue'),
        meta: { roles: ['admin'] }
      },
      {
        path: 'chat',
        name: 'ChatDialog',
        component: () => import('@/views/ChatDialog.vue'),
        meta: { roles: ['admin', 'user'] }
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
  const role = resolveRoleCode(getUserInfo())
  if (role === 'user') return '/chat'
  return '/dashboard'
}

router.beforeEach((to, from, next) => {
  // 离开智能对话时立刻中断 SSE，避免流式占用主线程拖死其它页面
  if (from.name === 'ChatDialog' && to.name !== 'ChatDialog') {
    try {
      useChatStore().abortCurrentStream()
    } catch {
      /* pinia 未就绪时忽略 */
    }
  }

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
    const userRole = resolveRoleCode(getUserInfo())
    if (!userRole || !to.meta.roles.includes(userRole)) {
      next(redirectByRole())
      return
    }
  }

  next()
})

export default router
