import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    const { code, msg, data } = response.data
    if (code === 0) {
      return data
    } else if (code === 401) {
      ElMessage.error('登录失效，请重新登录')
      const userStore = useUserStore()
      userStore.logout()
      window.location.href = '/login'
    } else if (code === 4001) {
      ElMessage.warning(msg || '您尚未被分配到任何用户组，请联系管理员')
      return Promise.reject(new Error(msg))
    } else if (code === 4002) {
      ElMessage.warning(msg || '文档正在处理中，请等待处理完成后再试')
      return Promise.reject(new Error(msg))
    } else if (code === 4003) {
      ElMessage.warning(msg || '系统品牌配置未初始化，使用默认值')
      return data || {}
    } else if (code === 403) {
      ElMessage.error(msg || '您无权访问该资源')
      return Promise.reject(new Error(msg))
    } else {
      ElMessage.error(msg || '请求失败')
      return Promise.reject(new Error(msg))
    }
  },
  (error) => {
    return Promise.reject(error)
  }
)

export default request