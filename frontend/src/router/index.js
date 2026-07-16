import { h } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'

const EmptyView = {
  name: 'EmptyView',
  render() {
    return h('div')
  }
}

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: EmptyView
      },
      {
        path: 'roles',
        name: 'Roles',
        component: EmptyView
      },
      {
        path: 'users',
        name: 'Users',
        component: EmptyView
      },
      {
        path: 'models',
        name: 'Models',
        component: EmptyView
      },
      {
        path: 'knowledge-bases',
        name: 'KnowledgeBases',
        component: () => import('@/views/KbManage.vue')
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/DocManage.vue')
      },
      {
        path: 'hit-test',
        name: 'HitTest',
        component: () => import('@/views/HitTest.vue')
      },
      {
        path: 'chat',
        name: 'ChatDialog',
        component: () => import('@/views/ChatDialog.vue')
      }
    ]
  },
  { path: '/kb', redirect: '/knowledge-bases' },
  { path: '/doc', redirect: '/documents' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
