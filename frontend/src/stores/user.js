/**
 * 用户 Pinia Store
 * - 兼容前端 A 登录页 setToken / setUserInfo
 * - 登出 / 切账号时调用 chatStore.resetState，防止跨账号污染
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import request from '@/utils/request'
import { useChatStore } from '@/stores/chat'

const TOKEN_KEY = 'rag_token'
const USER_KEY = 'rag_user'
const LEGACY_TOKEN_KEY = 'token'
const LEGACY_USER_KEY = 'userInfo'

function readCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY) || localStorage.getItem(LEGACY_USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || localStorage.getItem(LEGACY_TOKEN_KEY) || '')
  const userInfo = ref(readCachedUser())

  const isLoggedIn = computed(() => !!token.value)

  function setSession(nextToken, nextUser = null) {
    token.value = nextToken || ''
    userInfo.value = nextUser

    if (nextToken) {
      localStorage.setItem(TOKEN_KEY, nextToken)
      localStorage.setItem(LEGACY_TOKEN_KEY, nextToken)
    } else {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(LEGACY_TOKEN_KEY)
    }

    if (nextUser) {
      localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
      localStorage.setItem(LEGACY_USER_KEY, JSON.stringify(nextUser))
    } else {
      localStorage.removeItem(USER_KEY)
      localStorage.removeItem(LEGACY_USER_KEY)
    }
  }

  function setToken(nextToken) {
    setSession(nextToken, userInfo.value)
  }

  function setUserInfo(nextUser) {
    setSession(token.value, nextUser)
  }

  function clearAccountScopedState() {
    const chatStore = useChatStore()
    chatStore.resetState()
  }

  async function login(credentials) {
    try {
      clearAccountScopedState()
      const res = await request.post('/api/auth/login', credentials)
      const data = res.data || {}
      const nextToken = data.token || data.access_token || ''
      const nextUser = data.user || data
      setSession(nextToken, nextUser)
      return data
    } catch (error) {
      throw error
    }
  }

  function logout() {
    clearAccountScopedState()
    setSession('', null)
    localStorage.removeItem('currentRole')
    window.location.href = '/login'
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    setSession,
    setToken,
    setUserInfo,
    login,
    logout,
    clearAccountScopedState
  }
})
