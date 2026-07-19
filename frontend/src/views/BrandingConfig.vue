<template>
  <div class="branding-config page-shell">
    <div class="page-header">
      <h2>自定义设置</h2>
      <el-button v-if="isAdmin" type="primary" @click="handleReset">恢复默认</el-button>
    </div>

    <div class="page-body">
    <div class="config-container" :class="{ 'config-container--solo': !isAdmin }">
      <div class="config-form">
        <el-form
          class="branding-form"
          :model="form"
          :rules="formRules"
          ref="formRef"
          label-width="132px"
        >
          <template v-if="isAdmin">
            <el-form-item prop="brand_name" label="系统名称">
              <el-input
                v-model="form.brand_name"
                maxlength="10"
                show-word-limit
                placeholder="最多 10 个字"
              />
            </el-form-item>

            <el-form-item label="Logo 上传" class="form-item--top">
              <div class="logo-upload-block">
                <div v-if="previewLogoUrl" class="logo-preview">
                  <img :src="previewLogoUrl" alt="Logo预览" />
                </div>
                <div class="logo-actions">
                  <el-upload
                    class="logo-uploader"
                    action="#"
                    :auto-upload="false"
                    :limit="1"
                    :show-file-list="false"
                    :accept="'image/png,image/jpeg,image/jpg,image/webp,image/gif,image/svg+xml'"
                    v-model:file-list="logoFileList"
                    :on-change="handleLogoChange"
                  >
                    <el-button type="primary">上传</el-button>
                  </el-upload>
                  <el-button :disabled="!canEditLogo" @click="handleEditLogo">修改</el-button>
                </div>
                <div class="logo-tip">支持 png/jpg/webp/svg，最大 2MB；保存后保留最近 3 张便于回选</div>
                <div v-if="displayLogoHistory.length" class="logo-history">
                  <div class="logo-history__title">历史 Logo</div>
                  <div class="logo-history__list">
                    <button
                      v-for="(url, idx) in displayLogoHistory"
                      :key="`${url}-${idx}`"
                      type="button"
                      class="logo-history__item"
                      :class="{ 'is-active': isSameLogo(url, previewLogoUrl) }"
                      :title="'回选历史 Logo'"
                      @click="pickHistoryLogo(url)"
                    >
                      <img :src="url" alt="" />
                    </button>
                  </div>
                </div>
              </div>
            </el-form-item>

            <LogoCropDialog
              v-model="cropVisible"
              :image-url="cropSourceUrl"
              @confirm="onCropConfirm"
              @cancel="onCropCancel"
            />
          </template>

          <el-form-item prop="brand_theme_color" label="主题色" class="form-item--top">
            <div class="theme-swatches" role="listbox" aria-label="主题色">
              <button
                v-for="preset in themePresets"
                :key="preset.id"
                type="button"
                class="theme-swatch"
                role="option"
                :aria-selected="form.brand_theme_color === preset.value"
                :class="{ 'is-active': form.brand_theme_color === preset.value }"
                :title="`${preset.label} ${preset.value}`"
                :style="{ '--swatch': preset.value }"
                @click="selectThemeColor(preset.value)"
              >
                <span class="theme-swatch__dot" />
                <span class="theme-swatch__label">{{ preset.label }}</span>
              </button>
            </div>
          </el-form-item>

          <el-form-item label="个人头像">
            <div class="avatar-upload-block">
              <button type="button" class="avatar-preview-btn" title="更换头像" @click="triggerAvatarPick">
                <img
                  v-if="avatarPreviewUrl && !avatarBroken"
                  :src="avatarPreviewUrl"
                  alt=""
                  class="avatar-preview-img"
                  @error="avatarBroken = true"
                />
                <span v-else class="avatar-preview-fallback">{{ avatarFallback }}</span>
              </button>
              <div class="avatar-actions">
                <el-button type="primary" @click="triggerAvatarPick">更换头像</el-button>
                <span class="logo-tip">支持 png/jpg/webp，裁剪后立即生效</span>
              </div>
            </div>
            <input
              ref="avatarInputRef"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              class="avatar-file-input"
              @change="onAvatarFileChange"
            />
            <LogoCropDialog
              v-model="avatarCropVisible"
              :image-url="avatarCropSourceUrl"
              :output-size="256"
              @confirm="onAvatarCropConfirm"
              @cancel="onAvatarCropCancel"
            />
          </el-form-item>

          <template v-if="isAdmin">
            <el-form-item prop="brand_login_title" label="登录浮窗副标题">
              <el-input
                v-model="form.brand_login_title"
                maxlength="24"
                show-word-limit
                placeholder="显示在登录浮窗「欢迎使用」下方"
              />
            </el-form-item>

            <el-form-item prop="brand_footer_text" label="侧栏页脚">
              <el-input
                v-model="form.brand_footer_text"
                maxlength="24"
                show-word-limit
                placeholder="左侧导航栏底部文案，最多 24 字"
              />
            </el-form-item>
          </template>

          <el-form-item>
            <el-button type="primary" @click="handleSubmit" :loading="loading">保存配置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div v-if="isAdmin" class="config-preview">
        <h3>实时预览 · 登录浮窗</h3>
        <div
          class="brand-login-preview"
          :style="{ '--el-color-primary': form.brand_theme_color }"
        >
          <div class="brand-login-preview__viewport">
            <div class="brand-login-preview__scale">
              <div class="brand-login-preview__card" aria-hidden="true">
                <button type="button" class="modal-close" tabindex="-1">×</button>

                <div class="login-header">
                  <div class="logo-frame">
                    <img
                      v-if="previewLogoUrl && !previewLogoBroken"
                      :src="previewLogoUrl"
                      alt=""
                      class="logo-img"
                      @error="previewLogoBroken = true"
                    />
                    <div v-else class="logo-fallback" />
                  </div>
                  <h2>欢迎使用</h2>
                  <p class="login-header__sub">
                    {{ form.brand_login_title || '登录您的账户' }}
                  </p>
                </div>

                <div class="login-tabs" role="tablist">
                  <button
                    type="button"
                    class="tab-item"
                    :class="{ active: previewLoginType === 'employee' }"
                    @click="previewLoginType = 'employee'"
                  >
                    员工登录
                  </button>
                  <button
                    type="button"
                    class="tab-item"
                    :class="{ active: previewLoginType === 'admin' }"
                    @click="previewLoginType = 'admin'"
                  >
                    管理员登录
                  </button>
                </div>

                <div class="login-form">
                  <div class="login-field">
                    <label class="login-field-label">用户名</label>
                    <div class="preview-input">
                      <el-icon class="preview-input__icon"><User /></el-icon>
                      <span class="preview-input__ph">请输入用户名</span>
                    </div>
                  </div>
                  <div class="login-field login-field--password">
                    <label class="login-field-label">密码</label>
                    <div class="preview-input">
                      <el-icon class="preview-input__icon"><Lock /></el-icon>
                      <span class="preview-input__ph">请输入密码</span>
                      <el-icon class="preview-input__eye"><Hide /></el-icon>
                    </div>
                  </div>
                  <div class="login-pwd-row">
                    <p class="login-error is-placeholder">用户名或密码错误，请重新输入</p>
                    <span class="login-aux-link">忘记密码？</span>
                  </div>
                  <button type="button" class="login-btn" tabindex="-1">登录</button>
                </div>

                <p class="login-footer-aux">
                  没有账号？
                  <span class="login-aux-link">申请授权</span>
                </p>
              </div>
            </div>
          </div>
        </div>
        <p class="modal-preview__aside-hint">
          侧栏页脚：{{ form.brand_footer_text || '（未填写）' }}
        </p>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { updateBrandingApi } from '@/api/branding'
import { uploadAvatarApi } from '@/api/auth'
import { useBrandingStore } from '@/stores/branding'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { User, Lock, Hide } from '@element-plus/icons-vue'
import LogoCropDialog from '@/components/LogoCropDialog.vue'
import { nearestThemePreset, themePresetsForMode } from '@/constants/themePresets'
import { isAdminRole, resolveRoleCode } from '@/utils/role'
import { useUiPrefsStore } from '@/stores/uiPrefs'

const formRef = ref(null)
const loading = ref(false)
const logoFileList = ref([])
const brandingStore = useBrandingStore()
const userStore = useUserStore()
const uiPrefs = useUiPrefsStore()
const themePresets = computed(() => themePresetsForMode(uiPrefs.colorMode))
const previewLoginType = ref('employee')
const previewLogoBroken = ref(false)

const isAdmin = computed(() => isAdminRole(resolveRoleCode(userStore.userInfo)))

const avatarInputRef = ref(null)
const avatarCropVisible = ref(false)
const avatarCropSourceUrl = ref('')
const avatarBroken = ref(false)
let avatarPendingObjectUrl = ''

const avatarPreviewUrl = computed(() => String(userStore.userInfo?.avatar_url || '').trim())
const avatarFallback = computed(() => {
  const name = String(userStore.userInfo?.display_name || userStore.userInfo?.username || 'U').trim()
  return name.slice(0, 1).toUpperCase() || 'U'
})

const cropVisible = ref(false)
const cropSourceUrl = ref('')
/** 上传流程中临时源图；确认后转入 logoSourceUrl 供「修改」重裁 */
let pendingSourceObjectUrl = ''
/** 可再次框选的原图（blob 或已保存地址） */
const logoSourceUrl = ref('')
let logoSourceObjectUrl = ''
let previewObjectUrl = ''
/** 当前裁剪是「上传」还是「修改」 */
const cropFromEdit = ref(false)
const previewLogoUrl = ref('')
/** 回选历史 Logo 的 URL（保存时提交，与新上传互斥） */
const historyPickUrl = ref('')
const localHistory = ref([])
const canEditLogo = computed(() => Boolean(previewLogoUrl.value || logoSourceUrl.value))
const displayLogoHistory = computed(() => {
  const fromStore = brandingStore.brandLogoHistory || []
  const merged = [...localHistory.value, ...fromStore]
  const seen = new Set()
  const out = []
  for (const url of merged) {
    const key = String(url).split('?')[0]
    if (!key || seen.has(key)) continue
    seen.add(key)
    out.push(url)
    if (out.length >= 3) break
  }
  return out
})

function isSameLogo(a, b) {
  return String(a || '').split('?')[0] === String(b || '').split('?')[0]
}

function revokeUrl(url) {
  if (url && String(url).startsWith('blob:')) URL.revokeObjectURL(url)
}

function clearPendingSource() {
  if (pendingSourceObjectUrl && pendingSourceObjectUrl !== logoSourceObjectUrl) {
    revokeUrl(pendingSourceObjectUrl)
  }
  pendingSourceObjectUrl = ''
}

const form = reactive({
  brand_name: '',
  brand_theme_color: '#3D9BFF',
  brand_login_title: '',
  brand_footer_text: ''
})

const rules = {
  brand_name: [
    { required: true, message: '请输入系统名称', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        const text = String(value || '').trim()
        if (!text) {
          callback(new Error('请输入系统名称'))
          return
        }
        if ([...text].length > 10) {
          callback(new Error('系统名称最多 10 个字'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ],
  brand_theme_color: [{ required: true, message: '请选择主题色', trigger: 'change' }],
  brand_login_title: [{ required: true, message: '请输入登录浮窗副标题', trigger: 'blur' }],
  brand_footer_text: [
    { required: true, message: '请输入侧栏页脚', trigger: 'blur' },
    { max: 24, message: '侧栏页脚最多 24 个字', trigger: 'blur' }
  ]
}

/** 普通用户只校验主题色 */
const formRules = computed(() => {
  if (isAdmin.value) return rules
  return {
    brand_theme_color: rules.brand_theme_color
  }
})

function clearAvatarPending() {
  if (avatarPendingObjectUrl) {
    URL.revokeObjectURL(avatarPendingObjectUrl)
    avatarPendingObjectUrl = ''
  }
}

function triggerAvatarPick() {
  avatarInputRef.value?.click()
}

function onAvatarFileChange(e) {
  const file = e?.target?.files?.[0]
  if (avatarInputRef.value) avatarInputRef.value.value = ''
  if (!file) return
  if (!file.type?.startsWith('image/')) {
    ElMessage.error('请上传图片文件')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('头像文件不能超过 2MB')
    return
  }
  clearAvatarPending()
  avatarPendingObjectUrl = URL.createObjectURL(file)
  avatarCropSourceUrl.value = avatarPendingObjectUrl
  avatarCropVisible.value = true
}

async function onAvatarCropConfirm({ file }) {
  avatarCropVisible.value = false
  avatarCropSourceUrl.value = ''
  clearAvatarPending()
  try {
    const user = await uploadAvatarApi(file)
    if (user) userStore.setUserInfo({ ...userStore.userInfo, ...user })
    avatarBroken.value = false
    ElMessage.success('头像已更新')
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || error?.message || '头像上传失败')
  }
}

function onAvatarCropCancel() {
  avatarCropVisible.value = false
  avatarCropSourceUrl.value = ''
  clearAvatarPending()
}

const handleLogoChange = (file) => {
  const raw = file?.raw
  if (!raw) return
  if (!raw.type?.startsWith('image/')) {
    ElMessage.error('请上传图片文件')
    logoFileList.value = []
    return
  }
  if (raw.size > 2 * 1024 * 1024) {
    ElMessage.error('Logo 文件大小不能超过 2MB')
    logoFileList.value = []
    return
  }
  logoFileList.value = []
  clearPendingSource()
  historyPickUrl.value = ''
  pendingSourceObjectUrl = URL.createObjectURL(raw)
  cropSourceUrl.value = pendingSourceObjectUrl
  cropFromEdit.value = false
  cropVisible.value = true
}

function handleEditLogo() {
  const source = logoSourceUrl.value || previewLogoUrl.value
  if (!source) {
    ElMessage.warning('请先上传 Logo')
    return
  }
  historyPickUrl.value = ''
  cropSourceUrl.value = source
  cropFromEdit.value = true
  cropVisible.value = true
}

function pickHistoryLogo(url) {
  if (!url) return
  historyPickUrl.value = url
  logoFileList.value = []
  clearPendingSource()
  revokeUrl(previewObjectUrl)
  previewObjectUrl = ''
  previewLogoUrl.value = url
  logoSourceUrl.value = url
  ElMessage.success('已回选历史 Logo，请点击保存配置生效')
}

function onCropConfirm({ file, previewUrl }) {
  historyPickUrl.value = ''
  // 新上传：把 pending 原图固化为可再次修改的源
  if (!cropFromEdit.value && pendingSourceObjectUrl) {
    if (logoSourceObjectUrl && logoSourceObjectUrl !== pendingSourceObjectUrl) {
      revokeUrl(logoSourceObjectUrl)
    }
    logoSourceObjectUrl = pendingSourceObjectUrl
    logoSourceUrl.value = pendingSourceObjectUrl
    pendingSourceObjectUrl = ''
  } else {
    clearPendingSource()
  }
  cropSourceUrl.value = ''
  cropFromEdit.value = false

  revokeUrl(previewObjectUrl)
  previewObjectUrl = previewUrl
  previewLogoUrl.value = previewUrl
  logoFileList.value = [
    {
      name: file.name,
      raw: file,
      uid: Date.now(),
      status: 'ready'
    }
  ]
}

function onCropCancel() {
  clearPendingSource()
  cropSourceUrl.value = ''
  // 修改取消：保留已有 Logo；上传取消：不改动已有预览
  if (!cropFromEdit.value) {
    logoFileList.value = logoFileList.value.filter((f) => f?.raw)
  }
  cropFromEdit.value = false
}

const handleThemeColorChange = () => {
  document.documentElement.style.setProperty('--el-color-primary', form.brand_theme_color)
  document.documentElement.style.setProperty('--color-primary', form.brand_theme_color)
}

function selectThemeColor(value) {
  form.brand_theme_color = value
  handleThemeColorChange()
}

const initForm = () => {
  form.brand_name = brandingStore.brandName
  form.brand_theme_color = nearestThemePreset(
    brandingStore.brandThemeColor,
    uiPrefs.colorMode
  ).value
  form.brand_login_title = brandingStore.brandLoginTitle
  form.brand_footer_text = brandingStore.brandFooterText
  localHistory.value = [...(brandingStore.brandLogoHistory || [])]
  historyPickUrl.value = ''
  const logoUrl = brandingStore.brandLogoUrl
  if (logoUrl) {
    previewLogoUrl.value = logoUrl
    logoSourceUrl.value = logoUrl
  }
  handleThemeColorChange()
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    const data = new FormData()
    data.append('brand_theme_color', form.brand_theme_color)

    if (isAdmin.value) {
      data.append('brand_name', form.brand_name)
      data.append('brand_login_title', form.brand_login_title)
      data.append('brand_footer_text', form.brand_footer_text)

      const logoRaw = logoFileList.value.find((f) => f?.raw)?.raw
      if (logoRaw) {
        data.append('brand_logo', logoRaw, logoRaw.name || 'logo.png')
      } else if (historyPickUrl.value) {
        data.append('brand_logo_history_pick', historyPickUrl.value)
      }
    }

    const updateResult = await updateBrandingApi(data)
    await brandingStore.fetchBranding()
    brandingStore.applyBranding()

    ElMessage.success('自定义设置更新成功')

    if (isAdmin.value) {
      const logoUrl = updateResult?.brand_logo_url || brandingStore.brandLogoUrl
      if (logoUrl) {
        revokeUrl(previewObjectUrl)
        previewObjectUrl = ''
        previewLogoUrl.value = logoUrl
        logoSourceUrl.value = logoUrl
        revokeUrl(logoSourceObjectUrl)
        logoSourceObjectUrl = ''
      }
      localHistory.value = [...(brandingStore.brandLogoHistory || [])]
      historyPickUrl.value = ''
      logoFileList.value = []
    }
  } catch (error) {
    console.error('handleSubmit error:', error)
    if (error.response?.status === 422) {
      const errorMsg = error.response.data?.detail || error.response.data?.message || '参数格式错误'
      ElMessage.error(errorMsg)
    } else {
      ElMessage.error(error?.response?.data?.msg || '自定义设置更新失败')
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
    clearPendingSource()
    revokeUrl(logoSourceObjectUrl)
    logoSourceObjectUrl = ''
    logoSourceUrl.value = ''
    revokeUrl(previewObjectUrl)
    previewObjectUrl = ''
    previewLogoUrl.value = ''
    historyPickUrl.value = ''
    localHistory.value = []
    ElMessage.success('已恢复默认配置')
  } catch (error) {
    console.error(error)
  }
}

watch(() => previewLogoUrl.value, () => {
  previewLogoBroken.value = false
})

watch(() => avatarPreviewUrl.value, () => {
  avatarBroken.value = false
})

watch(() => brandingStore.brandThemeColor, (newColor) => {
  form.brand_theme_color = nearestThemePreset(newColor, uiPrefs.colorMode).value
})

/** 切换日夜间：色盘换列；若当前色不在该模式列表，回落到冰蓝 */
watch(
  () => uiPrefs.colorMode,
  (mode) => {
    const list = themePresetsForMode(mode)
    const still = list.some(
      (p) => p.value.toUpperCase() === String(form.brand_theme_color || '').toUpperCase()
    )
    if (!still) {
      const next = nearestThemePreset(form.brand_theme_color, mode).value
      form.brand_theme_color = next
      handleThemeColorChange()
    }
  }
)

onMounted(() => {
  initForm()
})

onBeforeUnmount(() => {
  clearPendingSource()
  clearAvatarPending()
  revokeUrl(logoSourceObjectUrl)
  revokeUrl(previewObjectUrl)
})
</script>

<style scoped>
.branding-config {
  /* page-shell 由 admin.css 统一 */
}
.config-container {
  display: flex;
  gap: 20px;
  align-items: stretch;
  width: 100%;
}
.config-container--solo .config-form {
  flex: 1 1 100%;
  max-width: 640px;
}
.config-form {
  flex: 1 1 55%;
  min-width: 0;
  max-width: none;
  background: transparent;
  border: 1px solid var(--border-color);
  padding: 20px;
  border-radius: var(--radius-card);
  box-sizing: border-box;
}

/* Logo 上传 / 主题色：标签与多行内容上对齐 */
.config-form :deep(.form-item--top.el-form-item) {
  align-items: flex-start !important;
}

.config-form :deep(.form-item--top .el-form-item__label-wrap),
.config-form :deep(.form-item--top .el-form-item__label) {
  align-items: flex-start !important;
  height: auto !important;
  min-height: var(--admin-control-height, 32px);
  line-height: 32px !important;
  padding-top: 0 !important;
}

.config-form :deep(.form-item--top .el-form-item__content) {
  align-items: flex-start;
  line-height: normal;
}
.avatar-file-input {
  display: none;
}
.avatar-upload-block {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.avatar-preview-btn {
  padding: 0;
  margin: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 50%;
  line-height: 0;
}
.avatar-preview-img,
.avatar-preview-fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid color-mix(in srgb, var(--el-color-primary) 40%, transparent);
}
.avatar-preview-fallback {
  font-size: 22px;
  font-weight: 700;
  color: var(--admin-text);
  background: var(--admin-fill);
}
.avatar-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}
.config-preview {
  flex: 1 1 45%;
  min-width: 0;
  max-width: none;
  background: transparent;
  border: 1px solid var(--border-color);
  padding: 16px 14px 18px;
  border-radius: var(--radius-card);
  box-sizing: border-box;
}
.config-preview h3 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 16px;
  color: var(--text-color-primary);
}

/* —— 登录浮窗真实预览（同比例放大） —— */
.brand-login-preview {
  --preview-scale: 0.92;
  --preview-width: 520px;
  --preview-height: 640px;
  --login-text: #f5f5f5;
  --login-text-muted: #9a9a9a;
  --login-text-dim: #6e6e6e;
  --login-font-sans: 'DM Sans', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  border-radius: 12px;
  background: #050505;
  padding: 20px 12px 18px;
  overflow: hidden;
}
.brand-login-preview__viewport {
  position: relative;
  width: 100%;
  height: calc(var(--preview-height) * var(--preview-scale));
  display: flex;
  justify-content: center;
}
.brand-login-preview__scale {
  position: absolute;
  top: 0;
  left: 50%;
  width: var(--preview-width);
  transform: translateX(-50%) scale(var(--preview-scale));
  transform-origin: top center;
}
.brand-login-preview__card {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 24px;
  color: var(--login-text);
  border: 1px solid rgba(120, 155, 220, 0.38);
  background-color: transparent;
  background-image: linear-gradient(
    180deg,
    rgba(6, 8, 14, 0.78) 0%,
    rgba(10, 13, 24, 0.62) 38%,
    rgba(15, 23, 40, 0.4) 68%,
    rgba(22, 38, 66, 0.25) 100%
  );
  -webkit-backdrop-filter: blur(18px) saturate(1.05);
  backdrop-filter: blur(18px) saturate(1.05);
  box-shadow:
    0 28px 56px rgba(0, 0, 0, 0.42),
    0 8px 20px rgba(0, 0, 0, 0.28),
    0 0 0 1px rgba(120, 160, 230, 0.13),
    inset 0 0 0 1px rgba(150, 180, 235, 0.1);
}
.brand-login-preview__card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  z-index: 0;
  opacity: 0.38;
  mix-blend-mode: soft-light;
  background-image:
    repeating-radial-gradient(
      circle at 20% 24%,
      rgba(255, 255, 255, 0.048) 0 0.55px,
      transparent 0.9px 2.8px
    ),
    repeating-radial-gradient(
      circle at 72% 70%,
      rgba(185, 205, 240, 0.035) 0 0.5px,
      transparent 0.85px 3.2px
    );
}
.brand-login-preview__card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  z-index: 0;
  background: linear-gradient(
    180deg,
    transparent 0%,
    transparent 48%,
    rgba(70, 110, 180, 0.07) 74%,
    rgba(80, 120, 200, 0.12) 100%
  );
}
.brand-login-preview__card > * {
  position: relative;
  z-index: 1;
}
.brand-login-preview .modal-close {
  position: absolute;
  top: 10px;
  right: 14px;
  z-index: 3;
  border: 0;
  background: transparent;
  color: var(--login-text-muted);
  font-size: 24px;
  line-height: 1;
  cursor: default;
  pointer-events: none;
}
.brand-login-preview .login-header {
  padding: 32px 48px 18px;
  text-align: center;
}
.brand-login-preview .logo-frame {
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.brand-login-preview .logo-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.brand-login-preview .logo-fallback {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--el-color-primary) 70%, #fff),
    var(--el-color-primary)
  );
}
.brand-login-preview .login-header h2 {
  margin: 0 0 8px;
  font-family: var(--login-font-sans);
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 0.03em;
  line-height: 1.3;
  color: var(--login-text);
}
.brand-login-preview .login-header__sub {
  margin: 0;
  color: rgba(200, 200, 205, 0.55);
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  word-break: break-word;
}
.brand-login-preview .login-tabs {
  display: flex;
  margin: 0 40px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.18);
  overflow: hidden;
}
.brand-login-preview .tab-item {
  flex: 1;
  appearance: none;
  border: 0;
  background: transparent;
  padding: 14px 0;
  cursor: pointer;
  color: var(--login-text-muted);
  font-size: 15px;
  letter-spacing: 0.06em;
  transition: color 0.25s ease, background 0.25s ease;
}
.brand-login-preview .tab-item.active {
  color: #fff;
  font-weight: 600;
  background: color-mix(in srgb, var(--el-color-primary) 28%, transparent);
}
.brand-login-preview .login-form {
  padding: 22px 48px 12px;
}
.brand-login-preview .login-field {
  margin-bottom: 22px;
}
.brand-login-preview .login-field--password {
  margin-bottom: 14px;
}
.brand-login-preview .login-field-label {
  display: block;
  color: rgba(235, 235, 240, 0.88);
  font-size: 15px;
  font-weight: 600;
  padding-bottom: 8px;
  line-height: 1.35;
}
.brand-login-preview .preview-input {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 54px;
  padding: 0 14px;
  border-radius: 12px;
  background: rgba(6, 8, 14, 0.55);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset;
}
.brand-login-preview .preview-input__icon,
.brand-login-preview .preview-input__eye {
  color: var(--login-text-muted);
  flex-shrink: 0;
}
.brand-login-preview .preview-input__ph {
  flex: 1;
  color: var(--login-text-dim);
  font-size: 17px;
}
.brand-login-preview .login-pwd-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 2px 0 20px;
  min-height: 28px;
}
.brand-login-preview .login-error {
  flex: 1;
  margin: 0;
  font-size: 14px;
  line-height: 1.75;
  color: transparent;
  user-select: none;
}
.brand-login-preview .login-aux-link {
  flex-shrink: 0;
  color: rgba(180, 180, 190, 0.42);
  font-size: 14px;
}
.brand-login-preview .login-btn {
  width: 100%;
  height: 56px;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.14em;
  border-radius: 12px;
  border: 0;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset;
  cursor: default;
  pointer-events: none;
}
.brand-login-preview .login-footer-aux {
  margin: 0;
  padding: 8px 48px 36px;
  text-align: center;
  font-size: 14px;
  line-height: 1.65;
  color: rgba(180, 180, 190, 0.38);
}
.brand-login-preview .login-footer-aux .login-aux-link {
  margin-left: 4px;
}

.modal-preview__aside-hint {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--admin-text-dim, var(--text-color-secondary));
  line-height: 1.5;
}
.logo-upload-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
}
.logo-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo-uploader {
  margin-bottom: 0;
}
.logo-uploader :deep(.el-upload) {
  display: inline-flex;
}
.logo-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
.logo-preview {
  margin: 0;
}
.logo-preview img {
  width: 140px;
  height: 140px;
  object-fit: cover;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  display: block;
}

.logo-history {
  width: 100%;
  margin-top: 4px;
}
.logo-history__title {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--admin-text-muted, var(--text-color-secondary));
}
.logo-history__list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.logo-history__item {
  width: 56px;
  height: 56px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  cursor: pointer;
  overflow: hidden;
}
.logo-history__item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.logo-history__item:hover,
.logo-history__item.is-active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--el-color-primary) 25%, transparent);
}

.theme-swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.theme-swatch {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 76px;
  padding: 8px 4px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--admin-text-muted, var(--text-color-secondary));
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.theme-swatch:hover,
.theme-swatch.is-active {
  border-color: color-mix(in srgb, var(--swatch) 55%, transparent);
  background: color-mix(in srgb, var(--swatch) 12%, transparent);
}
.theme-swatch__dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--swatch);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.12);
}
.theme-swatch.is-active .theme-swatch__dot {
  box-shadow:
    0 0 0 2px rgba(255, 255, 255, 0.2),
    0 0 12px color-mix(in srgb, var(--swatch) 55%, transparent);
}
.theme-swatch__label {
  font-size: 11px;
  line-height: 1.2;
  text-align: center;
  white-space: nowrap;
}

</style>
<style>
html.admin-theme .branding-config .branding-form .el-form-item.form-item--top {
  align-items: flex-start !important;
}

html.admin-theme .branding-config .branding-form .el-form-item.form-item--top .el-form-item__label-wrap,
html.admin-theme .branding-config .branding-form .el-form-item.form-item--top .el-form-item__label {
  align-items: flex-start !important;
  height: auto !important;
  line-height: 32px !important;
}
</style>
