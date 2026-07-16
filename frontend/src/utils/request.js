/**
 * 全局 Axios 封装（前端 B 规范 + 兼容前端 A）
 * - 自动携带 JWT Token
 * - 自动附加 env 环境标识
 * - 统一错误码弹窗：0/400/401/403/404/500/5001/5002
 * - 成功时返回完整业务体 { code, message, data }，由各模块自行取 data
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const ERROR_MESSAGES = {
  400: '请求参数错误',
  401: '登录已过期，请重新登录',
  403: '无操作权限',
  404: '资源不存在',
  500: '服务异常，请稍后重试',
  5001: '向量库服务异常，请稍后重试或联系管理员',
  5002: '大模型服务异常，请稍后重试'
}

function getEnvTag() {
  return localStorage.getItem('rag_env') || import.meta.env.VITE_APP_ENV || 'dev'
}

function getToken() {
  return localStorage.getItem('rag_token') || localStorage.getItem('token') || ''
}

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 60000
})

request.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    const env = getEnvTag()
    if (config.method === 'get') {
      config.params = { ...(config.params || {}), env }
    } else if (config.data instanceof FormData) {
      config.params = { ...(config.params || {}), env }
    } else if (config.data && typeof config.data === 'object') {
      config.data = { ...config.data, env }
    } else {
      config.params = { ...(config.params || {}), env }
    }
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response.data
    }
    const res = response.data
    if (!res || typeof res.code === 'undefined') {
      return res
    }
    if (res.code === 0) {
      return res
    }
    const msg = ERROR_MESSAGES[res.code] || res.message || res.msg || '请求失败'
    ElMessage.error(msg)
    if (res.code === 401) {
      window.location.href = '/login'
    }
    return Promise.reject(res)
  },
  (error) => {
    if (axios.isCancel?.(error) || error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
      return Promise.reject(error)
    }
    const code = error?.response?.data?.code
    const msg =
      ERROR_MESSAGES[code] ||
      error?.response?.data?.message ||
      error?.response?.data?.msg ||
      error.message ||
      '网络异常，请稍后重试'
    ElMessage.error(msg)
    if (code === 401 || error?.response?.status === 401) {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default request
export { getEnvTag, getToken, ERROR_MESSAGES }
