/**
 * 用户 Pinia Store
 * 负责登录态、用户信息；登出 / 切换账号时联动清空聊天会话
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import request from '@/utils/request'
import { useChatStore } from '@/stores/chat'

const TOKEN_KEY = 'rag_token'
const USER_KEY = 'rag_user'
const LEGACY_TOKEN_KEY = 'token'
const LEGACY_USER_KEY = 'userInfo'

/** 从本地缓存恢复用户信息 */
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

  /**
   * 写入登录态到内存与 localStorage
   * @param {string} nextToken JWT
   * @param {Object|null} nextUser 用户信息
   */
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

  /** 兼容旧登录页调用方式 */
  function setToken(nextToken) {
    setSession(nextToken, userInfo.value)
  }

  /** 兼容旧登录页调用方式 */
  function setUserInfo(nextUser) {
    setSession(token.value, nextUser)
  }

  /**
   * 清空跨账号残留状态
   * 登出、切换账号前统一调用，防止会话数据污染
   */
  function clearAccountScopedState() {
    const chatStore = useChatStore()
    chatStore.resetState()
  }

  /**
   * 用户登录
   * 切换账号时先 resetState，再写入新登录态
   */
  async function login(credentials) {
    try {
      // 切换账号：先清空上一账号会话与流式状态
      clearAccountScopedState()

      const res = await request.post('/api/auth/login', credentials)
      const data = res.data || {}
      const nextToken = data.token || data.access_token || ''
      const nextUser = data.user || data

      setSession(nextToken, nextUser)
      return data
    } catch (error) {
      // 异常交由全局 axios 统一处理
      throw error
    }
  }

  /**
   * 用户登出
   * 完整清空 token、用户信息，并 resetState 聊天模块
   */
  function logout() {
    clearAccountScopedState()
    setSession('', null)
    localStorage.removeItem('currentRole')
    window.location.hash = '#/dashboard'
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
