<template>
  <div class="branding-config">
    <div class="page-header">
      <h2>品牌配置</h2>
      <el-button type="primary" @click="handleReset">恢复默认</el-button>
    </div>
    
    <div class="config-container">
      <div class="config-form">
        <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
          <el-form-item prop="brand_name" label="系统名称">
            <el-input v-model="form.brand_name" placeholder="请输入系统名称" />
          </el-form-item>
          
          <el-form-item label="Logo 上传">
            <el-upload
              class="logo-uploader"
              action="#"
              :auto-upload="false"
              :limit="1"
              :accept="'image/png,image/jpeg,image/svg+xml'"
              v-model:file-list="logoFileList"
              :on-change="handleLogoChange"
              :on-remove="handleLogoRemove"
            >
              <el-button type="primary">上传 Logo</el-button>
              <template #tip>
                <div class="el-upload__tip">支持 .png/.jpg/.svg 格式，最大 2MB</div>
              </template>
            </el-upload>
            <div v-if="previewLogoUrl" class="logo-preview">
              <img :src="previewLogoUrl" alt="Logo预览" />
            </div>
          </el-form-item>
          
          <el-form-item prop="brand_theme_color" label="主题色">
            <el-color-picker v-model="form.brand_theme_color" show-alpha @change="handleThemeColorChange" />
          </el-form-item>
          
          <el-form-item prop="brand_login_title" label="登录标语">
            <el-input v-model="form.brand_login_title" placeholder="请输入登录页标语" />
          </el-form-item>
          
          <el-form-item prop="brand_footer_text" label="页脚文案">
            <el-input v-model="form.brand_footer_text" placeholder="请输入页脚文案" />
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="handleSubmit" :loading="loading">保存配置</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <div class="config-preview">
        <h3>实时预览</h3>
        <div class="preview-card" :style="{ '--primary-color': form.brand_theme_color }">
          <div class="preview-header">
            <div class="preview-logo">
              <img v-if="previewLogoUrl" :src="previewLogoUrl" alt="Logo" />
              <div v-else class="default-logo"></div>
            </div>
            <div class="preview-title">{{ form.brand_name || '系统名称' }}</div>
          </div>
          <div class="preview-login">
            <div class="login-title">{{ form.brand_login_title || '登录标语' }}</div>
            <el-button type="primary" class="preview-btn">登录</el-button>
          </div>
          <div class="preview-footer">
            {{ form.brand_footer_text || '页脚文案' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { updateBrandingApi } from '@/api/branding'
import { useBrandingStore } from '@/stores/branding'
import { ElMessage } from 'element-plus'

const formRef = ref(null)
const loading = ref(false)
const logoFileList = ref([])
const brandingStore = useBrandingStore()

const form = reactive({
  brand_name: '',
  brand_theme_color: '#409EFF',
  brand_login_title: '',
  brand_footer_text: ''
})

const rules = {
  brand_name: [{ required: true, message: '请输入系统名称', trigger: 'blur' }],
  brand_theme_color: [{ required: true, message: '请选择主题色', trigger: 'change' }],
  brand_login_title: [{ required: true, message: '请输入登录标语', trigger: 'blur' }],
  brand_footer_text: [{ required: true, message: '请输入页脚文案', trigger: 'blur' }]
}

const previewLogoUrl = ref('')

const handleLogoChange = (file, files) => {
  const raw = file?.raw
  if (!raw) return
  if (raw.size > 2 * 1024 * 1024) {
    ElMessage.error('Logo 文件大小不能超过 2MB')
    logoFileList.value = []
    previewLogoUrl.value = ''
    return
  }
  // 受控 file-list：只保留最新一张
  logoFileList.value = files?.length ? [files[files.length - 1]] : [file]
  const reader = new FileReader()
  reader.onload = (e) => {
    previewLogoUrl.value = e.target.result
  }
  reader.readAsDataURL(raw)
}

const handleLogoRemove = () => {
  logoFileList.value = []
  previewLogoUrl.value = ''
}

const handleThemeColorChange = () => {
  document.documentElement.style.setProperty('--el-color-primary', form.brand_theme_color)
}

const initForm = () => {
  form.brand_name = brandingStore.brandName
  form.brand_theme_color = brandingStore.brandThemeColor
  form.brand_login_title = brandingStore.brandLoginTitle
  form.brand_footer_text = brandingStore.brandFooterText
  if (brandingStore.brandLogoUrl && brandingStore.brandLogoUrl !== '/uploads/branding/logo.png') {
    previewLogoUrl.value = brandingStore.brandLogoUrl
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    const data = new FormData()
    data.append('brand_name', form.brand_name)
    data.append('brand_theme_color', form.brand_theme_color)
    data.append('brand_login_title', form.brand_login_title)
    data.append('brand_footer_text', form.brand_footer_text)

    const logoRaw = logoFileList.value.find((f) => f?.raw)?.raw
    if (logoRaw) {
      data.append('brand_logo', logoRaw, logoRaw.name || 'logo.png')
    }

    const updateResult = await updateBrandingApi(data)
    await brandingStore.fetchBranding()

    ElMessage.success('品牌配置更新成功')

    const logoUrl = updateResult?.brand_logo_url || brandingStore.brandLogoUrl
    if (logoUrl && logoUrl !== '/uploads/branding/logo.png') {
      previewLogoUrl.value = logoUrl
    }
    logoFileList.value = []
  } catch (error) {
    console.error('handleSubmit error:', error)
    if (error.response?.status === 422) {
      const errorMsg = error.response.data?.detail || error.response.data?.message || '参数格式错误'
      ElMessage.error(errorMsg)
    } else {
      ElMessage.error('品牌配置更新失败')
    }
  } finally {
    loading.value = false
  }
}

const handleReset = async () => {
  try {
    brandingStore.resetToDefaults()
    initForm()
    logoFileList.value = []
    previewLogoUrl.value = ''
    ElMessage.success('已恢复默认配置')
  } catch (error) {
    console.error(error)
  }
}

watch(() => brandingStore.brandThemeColor, (newColor) => {
  form.brand_theme_color = newColor
})

onMounted(() => {
  initForm()
})
</script>

<style scoped>
.branding-config {
  padding: 10px 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
}
.config-container {
  display: flex;
  gap: 40px;
}
.config-form {
  flex: 1;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}
.config-preview {
  width: 350px;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}
.config-preview h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
}
.logo-uploader {
  margin-bottom: 10px;
}
.logo-preview {
  margin-top: 10px;
}
.logo-preview img {
  width: 80px;
  height: 80px;
  object-fit: contain;
  border: 1px solid #e6e6e6;
  border-radius: 8px;
}
.preview-card {
  border: 1px solid #e6e6e6;
  border-radius: 8px;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
}
.preview-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e6e6e6;
  margin-bottom: 20px;
}
.preview-logo img {
  width: 40px;
  height: 40px;
  object-fit: contain;
}
.default-logo {
  width: 40px;
  height: 40px;
  background-color: var(--primary-color, #409EFF);
  border-radius: 8px;
}
.preview-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}
.preview-login {
  text-align: center;
  padding: 20px;
}
.login-title {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 20px;
}
.preview-btn {
  width: 100%;
}
.preview-footer {
  text-align: center;
  padding-top: 15px;
  border-top: 1px solid #e6e6e6;
  font-size: 12px;
  color: #909399;
}
</style>