import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/kb' },
  {
    path: '/kb',
    name: 'KbManage',
    component: () => import('@/views/KbManage.vue')
  },
  {
    path: '/doc',
    name: 'DocManage',
    component: () => import('@/views/DocManage.vue')
  },
  {
    path: '/hit-test',
    name: 'HitTest',
    component: () => import('@/views/HitTest.vue')
  },
  {
    path: '/chat',
    name: 'ChatDialog',
    component: () => import('@/views/ChatDialog.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
