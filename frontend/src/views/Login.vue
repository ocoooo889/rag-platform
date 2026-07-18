<template>
  <div class="login-container">
    <div class="login-hero" aria-hidden="true">
      <div class="network-visual">
        <span class="node node-1"></span>
        <span class="node node-2"></span>
        <span class="node node-3"></span>
        <span class="node node-4"></span>
        <span class="node node-5"></span>
        <span class="node node-6"></span>
        <span class="line line-1"></span>
        <span class="line line-2"></span>
        <span class="line line-3"></span>
        <span class="line line-4"></span>
      </div>
      <div class="hero-copy">
        <h2>{{ brandingStore.brandLoginTitle }}</h2>
        <p>统一管理知识库、文档向量化与智能检索能力</p>
      </div>
    </div>
    <div class="login-card">
      <div class="login-tabs">
        <div 
          class="tab-item" 
          :class="{ active: loginType === 'employee' }"
          @click="switchLoginType('employee')"
        >
          员工登录
        </div>
        <div 
          class="tab-item" 
          :class="{ active: loginType === 'admin' }"
          @click="switchLoginType('admin')"
        >
          管理员登录
        </div>
      </div>
      <div class="login-header">
        <img
          v-if="brandingStore.brandLogoUrl && !logoBroken"
          :src="brandingStore.brandLogoUrl"
          alt="logo"
          class="logo-img"
          @error="onLogoError"
        />
        <div v-else class="logo-icon"></div>
        <h1>{{ brandingStore.brandName }}</h1>
        <p>{{ brandingStore.brandLoginTitle }}</p>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef" class="login-form">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" @click="handleLogin" :loading="loading">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBrandingStore } from '@/stores/branding'
import { loginApi } from '@/api/auth'
import { isAdminRole } from '@/utils/role'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const brandingStore = useBrandingStore()
const formRef = ref(null)
const loading = ref(false)
const loginType = ref('employee')
const logoBroken = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const switchLoginType = (type) => {
  loginType.value = type
}

const onLogoError = () => {
  logoBroken.value = true
}

onMounted(async () => {
  try {
    await brandingStore.fetchBranding()
  } catch (e) {
    /* 使用默认值 */
  }
})

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    const data = await loginApi(form)
    userStore.setToken(data.token)
    userStore.setUserInfo(data.user)

    const role = data.user.role

    if (loginType.value === 'admin' && !isAdminRole(role)) {
      ElMessage.error('当前账号无管理员权限，请使用员工登录')
      userStore.setSession('', null)
      return
    }

    ElMessage.success('登录成功')
    const redirectPath = isAdminRole(role) ? '/dashboard' : '/chat'
    router.push(redirectPath)
  } catch (error) {
    const msg =
      error?.message ||
      error?.msg ||
      error?.response?.data?.msg ||
      '用户名或密码错误，请重新输入'
    ElMessage.error(
      /用户名|密码|认证|unauthorized|401/i.test(String(msg))
        ? '用户名或密码错误，请重新输入'
        : msg
    )
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  position: relative;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 72px;
  height: 100vh;
  padding: 48px 15vw 48px 8vw;
  overflow: hidden;
  background:
    linear-gradient(rgba(74, 122, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(74, 122, 255, 0.035) 1px, transparent 1px),
    radial-gradient(circle at 20% 58%, rgba(74, 122, 255, 0.22), transparent 34%),
    linear-gradient(135deg, #f7fbff 0%, #eef6ff 48%, #ffffff 100%);
  background-size: 24px 24px, 24px 24px, auto, auto;
}
.login-container::before {
  position: absolute;
  left: -8%;
  bottom: -18%;
  width: 58vw;
  height: 42vw;
  content: '';
  background: radial-gradient(ellipse, rgba(74, 122, 255, 0.18), rgba(74, 122, 255, 0));
}
.login-hero {
  position: relative;
  z-index: 1;
  flex: 1;
  max-width: 520px;
  min-height: 420px;
}
.network-visual {
  position: relative;
  width: 420px;
  height: 300px;
  margin: 0 auto;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 70%, rgba(255, 255, 255, 0.92), rgba(74, 122, 255, 0.08) 58%, transparent 72%);
}
.network-visual::before,
.network-visual::after {
  position: absolute;
  left: 74px;
  right: 74px;
  bottom: 28px;
  height: 1px;
  content: '';
  border-radius: 50%;
  border-top: 1px solid rgba(74, 122, 255, 0.26);
}
.network-visual::after {
  left: 118px;
  right: 118px;
  bottom: 48px;
}
.node {
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #8cd4ff, #1f7dff 68%, #125dd8);
  box-shadow: 0 8px 18px rgba(74, 122, 255, 0.28);
}
.node-1 { left: 126px; top: 70px; }
.node-2 { left: 208px; top: 46px; }
.node-3 { left: 282px; top: 96px; }
.node-4 { left: 178px; top: 142px; }
.node-5 { left: 112px; top: 184px; }
.node-6 { left: 246px; top: 206px; }
.line {
  position: absolute;
  height: 1px;
  background: rgba(74, 122, 255, 0.38);
  transform-origin: left center;
}
.line-1 { left: 143px; top: 82px; width: 78px; transform: rotate(-18deg); }
.line-2 { left: 222px; top: 59px; width: 82px; transform: rotate(34deg); }
.line-3 { left: 194px; top: 154px; width: 98px; transform: rotate(-24deg); }
.line-4 { left: 126px; top: 196px; width: 142px; transform: rotate(12deg); }
.hero-copy {
  margin-top: 18px;
  text-align: center;
}
.hero-copy h2 {
  margin: 0 0 10px;
  font-size: 28px;
  color: var(--text-color-primary);
}
.hero-copy p {
  margin: 0;
  color: var(--text-color-secondary);
}
.login-card {
  position: relative;
  z-index: 2;
  width: 420px;
  padding: 0;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 20px;
  box-shadow: 0 24px 56px rgba(74, 122, 255, 0.18);
  backdrop-filter: blur(12px);
}
.login-tabs {
  display: flex;
  background: #f8fbff;
  border-bottom: 1px solid var(--border-color-light);
}
.tab-item {
  flex: 1;
  text-align: center;
  padding: 15px 0;
  font-size: 14px;
  color: var(--text-color-regular);
  cursor: pointer;
  transition: all 0.3s;
}
.tab-item:hover {
  color: var(--color-primary);
}
.tab-item.active {
  color: var(--color-primary);
  font-weight: 600;
  border-bottom: 2px solid var(--color-primary);
}
.login-header {
  text-align: center;
  margin-bottom: 30px;
  padding: 30px 40px 0;
}
.logo-img {
  display: block;
  width: 60px;
  height: 60px;
  object-fit: contain;
  margin: 0 auto 15px;
  border-radius: 12px;
}
.logo-icon {
  width: 60px;
  height: 60px;
  position: relative;
  background: linear-gradient(135deg, #4a7aff 0%, #2f63e8 100%);
  border-radius: 18px;
  margin: 0 auto 15px;
  box-shadow: 0 12px 24px rgba(74, 122, 255, 0.28);
}
.logo-icon::before,
.logo-icon::after {
  position: absolute;
  left: 17px;
  width: 26px;
  height: 5px;
  content: '';
  border-radius: 999px;
  background: #ffffff;
}
.logo-icon::before {
  top: 20px;
}
.logo-icon::after {
  top: 33px;
}
.login-header h1 {
  margin: 0 0 5px;
  font-size: 24px;
  color: var(--text-color-primary);
}
.login-header p {
  margin: 0;
  color: var(--text-color-secondary);
}
.login-form {
  width: 100%;
  padding: 0 40px 40px;
}
.login-form :deep(.el-input__wrapper) {
  min-height: 42px;
  background: #fbfdff;
}
.login-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  border-radius: 10px;
}

@media (max-width: 960px) {
  .login-container {
    justify-content: center;
    padding: 32px;
  }

  .login-hero {
    display: none;
  }
}
</style>