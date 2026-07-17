<template>
  <div class="login-container">
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
        <div class="logo-icon" :style="{ backgroundColor: brandingStore.brandThemeColor }">
          <img v-if="brandingStore.brandLogoUrl && brandingStore.brandLogoUrl !== '/uploads/branding/logo.png'" :src="brandingStore.brandLogoUrl" alt="Logo" />
        </div>
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
          <el-button type="primary" class="login-btn" @click="handleLogin" :loading="loading" :style="{ backgroundColor: brandingStore.brandThemeColor, borderColor: brandingStore.brandThemeColor }">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-footer">{{ brandingStore.brandFooterText }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBrandingStore } from '@/stores/branding'
import { loginApi } from '@/api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const brandingStore = useBrandingStore()
const formRef = ref(null)
const loading = ref(false)
const loginType = ref('employee')

onMounted(() => {
  brandingStore.fetchBranding()
})

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

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    const data = await loginApi(form)
    userStore.setToken(data.token)
    userStore.setUserInfo(data.user)

    const roleName = data.user.role_name

    if (loginType.value === 'admin') {
      if (roleName !== '管理员' && roleName !== '编辑员') {
        ElMessage.error('当前账号无管理员权限，请使用员工登录')
        userStore.logout()
        return
      }
    }

    ElMessage.success('登录成功')

    let redirectPath = '/dashboard'
    if (roleName === '普通用户') {
      redirectPath = '/chat'
    } else if (roleName === '编辑员') {
      redirectPath = '/knowledge-bases'
    }
    router.push(redirectPath)
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  padding: 0;
  background-color: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.login-tabs {
  display: flex;
  border-bottom: 1px solid #ebeef5;
}
.tab-item {
  flex: 1;
  text-align: center;
  padding: 15px 0;
  font-size: 14px;
  color: #606266;
  cursor: pointer;
  transition: all 0.3s;
}
.tab-item:hover {
  color: #409eff;
}
.tab-item.active {
  color: #409eff;
  font-weight: 600;
  border-bottom: 2px solid #409eff;
}
.login-header {
  text-align: center;
  margin-bottom: 30px;
  padding: 30px 40px 0;
}
.logo-icon {
  width: 60px;
  height: 60px;
  background-color: #f56c6c;
  border-radius: 12px;
  margin: 0 auto 15px;
}
.login-header h1 {
  margin: 0 0 5px;
  font-size: 24px;
  color: #303133;
}
.login-header p {
  margin: 0;
  color: #909399;
}
.login-form {
  width: 100%;
  padding: 0 40px 40px;
}
.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}
.login-footer {
  text-align: center;
  padding: 15px 40px 30px;
  font-size: 12px;
  color: #909399;
}
.logo-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>