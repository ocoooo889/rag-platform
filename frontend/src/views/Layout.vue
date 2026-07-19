<template>
  <div class="layout-shell" :class="{ 'layout-shell--fill': isDashboardFill }">
    <EnvParticleField fixed />
    <header class="header">
      <div class="header-left">
        <h1 class="header-title" :title="displayBrandName">{{ displayBrandName }}</h1>
      </div>
      <div class="header-right">
        <div
          class="font-size-switch"
          role="group"
          aria-label="系统文字大小"
          title="系统文字大小"
        >
          <button
            v-for="opt in uiPrefs.options"
            :key="opt.value"
            type="button"
            class="font-size-switch__btn"
            :class="{ 'is-active': uiPrefs.fontSize === opt.value }"
            :aria-pressed="uiPrefs.fontSize === opt.value"
            @click="uiPrefs.setFontSize(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
        <div
          class="color-mode-switch"
          role="group"
          aria-label="界面模式"
          title="界面模式（仅管理后台；登录页不同步）"
        >
          <button
            v-for="opt in uiPrefs.colorModeOptions"
            :key="opt.value"
            type="button"
            class="color-mode-switch__btn"
            :class="{ 'is-active': uiPrefs.colorMode === opt.value }"
            :aria-pressed="uiPrefs.colorMode === opt.value"
            @click="uiPrefs.setColorMode(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
        <span class="user-chip">{{ displayRole }}</span>
        <el-dropdown
          trigger="click"
          placement="bottom-end"
          popper-class="user-menu-popper"
          @command="onUserMenuCommand"
        >
          <button type="button" class="user-avatar-btn" title="账户">
            <img
              v-if="headerAvatarUrl && !headerAvatarBroken"
              :src="headerAvatarUrl"
              alt="我的头像"
              class="user-avatar user-avatar--img"
              @error="headerAvatarBroken = true"
            />
            <span
              v-else
              class="user-avatar user-avatar--fallback"
              aria-hidden="true"
            >{{ headerAvatarFallback }}</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled class="user-menu-meta">
                <span class="user-menu-meta__name">{{ displayUserName }}</span>
                <span class="user-menu-meta__account">{{ displayAccount }}</span>
              </el-dropdown-item>
              <el-dropdown-item command="profile" divided>修改信息</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

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

        <el-dialog
          v-model="profileVisible"
          title="修改信息"
          width="440px"
          align-center
          destroy-on-close
          class="profile-dialog"
        >
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-width="96px"
          >
            <el-form-item label="头像">
              <div class="profile-avatar-row">
                <button type="button" class="user-avatar-btn profile-avatar-btn" @click="triggerAvatarPick">
                  <img
                    v-if="headerAvatarUrl && !headerAvatarBroken"
                    :src="headerAvatarUrl"
                    alt=""
                    class="user-avatar user-avatar--img"
                  />
                  <span v-else class="user-avatar user-avatar--fallback">{{ headerAvatarFallback }}</span>
                </button>
                <el-button @click="triggerAvatarPick">更换头像</el-button>
              </div>
            </el-form-item>
            <el-form-item label="账号">
              <el-input :model-value="displayAccount" disabled />
            </el-form-item>
            <el-form-item prop="display_name" label="用户名">
              <el-input v-model="profileForm.display_name" maxlength="32" show-word-limit placeholder="显示名称" />
            </el-form-item>
            <el-form-item prop="old_password" label="当前密码">
              <el-input
                v-model="profileForm.old_password"
                type="password"
                show-password
                placeholder="不修改密码可留空"
                autocomplete="current-password"
              />
            </el-form-item>
            <el-form-item prop="new_password" label="新密码">
              <el-input
                v-model="profileForm.new_password"
                type="password"
                show-password
                placeholder="不修改密码可留空"
                autocomplete="new-password"
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="profileVisible = false">取消</el-button>
            <el-button type="primary" :loading="profileSaving" @click="submitProfile">保存</el-button>
          </template>
        </el-dialog>
      </div>
    </header>
    <div class="layout-body" :class="{ 'layout-body--fill': isDashboardFill }">
      <aside class="aside">
        <div class="aside-brand">管理后台</div>
        <el-menu :default-active="activeMenu" class="menu" router>
          <el-menu-item v-if="canSeeMenu('/dashboard')" index="/dashboard">
            <el-icon><HomeFilled /></el-icon>
            <span class="menu-label">系统概览</span>
            <span v-if="isAdminOnlyPath('/dashboard')" class="admin-badge">admin</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/chat')" index="/chat">
            <el-icon><ChatDotRound /></el-icon>
            <span class="menu-label">智能对话</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/roles')" index="/roles">
            <el-icon><UserFilled /></el-icon>
            <span class="menu-label">权限管理</span>
            <span v-if="isAdminOnlyPath('/roles')" class="admin-badge">admin</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/user-groups')" index="/user-groups">
            <el-icon><UserFilled /></el-icon>
            <span class="menu-label">用户组管理</span>
            <span v-if="isAdminOnlyPath('/user-groups')" class="admin-badge">admin</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/users')" index="/users">
            <el-icon><User /></el-icon>
            <span class="menu-label">用户管理</span>
            <span v-if="isAdminOnlyPath('/users')" class="admin-badge">admin</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/models')" index="/models">
            <el-icon><Monitor /></el-icon>
            <span class="menu-label">大模型管理</span>
            <span v-if="isAdminOnlyPath('/models')" class="admin-badge">admin</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/branding')" index="/branding">
            <el-icon><Setting /></el-icon>
            <span class="menu-label">自定义设置</span>
            <span v-if="isAdminOnlyPath('/branding')" class="admin-badge">admin</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/knowledge-bases')" index="/knowledge-bases">
            <el-icon><Folder /></el-icon>
            <span class="menu-label">知识库管理</span>
            <span v-if="isAdminOnlyPath('/knowledge-bases')" class="admin-badge">admin</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/documents')" index="/documents">
            <el-icon><Document /></el-icon>
            <span class="menu-label">知识文档库</span>
            <span v-if="isAdminOnlyPath('/documents')" class="admin-badge">admin</span>
          </el-menu-item>
          <el-menu-item v-if="canSeeMenu('/hit-test')" index="/hit-test">
            <el-icon><Search /></el-icon>
            <span class="menu-label">命中率测试</span>
          </el-menu-item>
        </el-menu>
        <div v-if="showSidebarStatus" class="aside-status">
          <div class="aside-status__divider" aria-hidden="true" />
          <div class="aside-status__title">系统状态</div>
          <div
            v-for="item in sidebarStatusItems"
            :key="item.key"
            class="aside-status__item"
            :title="item.detail"
          >
            <span class="aside-status__dot" :class="`is-${item.status}`" />
            <div class="aside-status__body">
              <div class="aside-status__row">
                <span class="aside-status__label">{{ item.label }}</span>
                <span class="aside-status__tag" :class="`is-${item.status}`">
                  {{ statusText(item.status) }}
                </span>
              </div>
              <div class="aside-status__detail">{{ item.detail }}</div>
            </div>
          </div>
        </div>
        <div class="aside-spacer" aria-hidden="true" />
        <div class="aside-footer">{{ asideFooterText }}</div>
      </aside>
      <main class="main" :class="{ 'main--fill': isDashboardFill }">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBrandingStore } from '@/stores/branding'
import { useUiPrefsStore } from '@/stores/uiPrefs'
import { isAdminRole, resolveRoleCode, roleCodeToLabel } from '@/utils/role'
import {
  HomeFilled,
  UserFilled,
  User,
  Monitor,
  Folder,
  Document,
  Search,
  ChatDotRound,
  Setting
} from '@element-plus/icons-vue'
import EnvParticleField from '@/components/EnvParticleField.vue'
import LogoCropDialog from '@/components/LogoCropDialog.vue'
import { useGlassPointerGlow } from '@/composables/useGlassPointerGlow'
import { uploadAvatarApi, updateProfileApi } from '@/api/auth'
import { getStatsApi } from '@/api/dashboard'
import { ElMessage } from 'element-plus'

/** 登录页底部固定开发方署名；侧栏页脚读客户白标 brand_footer_text */
const PROVIDER_FOOTER = 'Powered by 六朵云 · RAG Platform'

const router = useRouter()
const userStore = useUserStore()
const brandingStore = useBrandingStore()
const uiPrefs = useUiPrefsStore()

useGlassPointerGlow()

const activeMenu = computed(() => router.currentRoute.value.path)
const isDashboardFill = computed(() => router.currentRoute.value.name === 'Dashboard')
/** 顶栏 Calendar 位：系统名称，最多 10 字 */
const displayBrandName = computed(() => {
  const name = String(brandingStore.brandName || '').trim()
  return name.slice(0, 10) || 'RAG平台'
})
/** 左侧导航底部：客户白标页脚（最多 24 字） */
const asideFooterText = computed(() => {
  const text = String(brandingStore.brandFooterText || '').trim().slice(0, 24)
  return text || PROVIDER_FOOTER
})

const sidebarServices = ref([])

const SIDEBAR_SERVICE_ORDER = ['api', 'chroma', 'bm25_cache', 'sqlite']

function statusText(status) {
  if (status === 'ok') return '正常'
  if (status === 'idle') return '空闲'
  if (status === 'warn') return '告警'
  if (status === 'down') return '异常'
  return '未知'
}

const sidebarStatusItems = computed(() => {
  const list = Array.isArray(sidebarServices.value) ? sidebarServices.value : []
  if (!list.length) {
    return [
      { key: 'api', label: '后端 API', status: 'idle', detail: '探测中…' },
      { key: 'chroma', label: 'Chroma 向量', status: 'idle', detail: '探测中…' },
      { key: 'bm25_cache', label: 'BM25 索引', status: 'idle', detail: '探测中…' }
    ]
  }
  const byKey = Object.fromEntries(list.map((s) => [s.key, s]))
  return SIDEBAR_SERVICE_ORDER.map((key) => byKey[key]).filter(Boolean).map((s) => ({
    key: s.key,
    label: s.label,
    status: s.status || 'idle',
    detail: s.detail || ''
  }))
})

const showSidebarStatus = computed(() => isAdminRole(resolveRoleCode(userStore.userInfo)))
const headerAvatarUrl = computed(() => String(userStore.userInfo?.avatar_url || '').trim())
const headerAvatarBroken = ref(false)
const headerAvatarFallback = computed(() => {
  const name = String(
    userStore.userInfo?.display_name || userStore.userInfo?.username || 'U'
  ).trim()
  const ch = name.slice(0, 1)
  return /[a-z]/.test(ch) ? ch.toUpperCase() : ch || 'U'
})
const displayUserName = computed(
  () => String(userStore.userInfo?.display_name || userStore.userInfo?.username || '用户').trim()
)
const displayAccount = computed(() => String(userStore.userInfo?.username || '').trim())
watch(headerAvatarUrl, () => {
  headerAvatarBroken.value = false
})

const avatarInputRef = ref(null)
const avatarCropVisible = ref(false)
const avatarCropSourceUrl = ref('')
let avatarPendingObjectUrl = ''

const profileVisible = ref(false)
const profileSaving = ref(false)
const profileFormRef = ref(null)
const profileForm = reactive({
  display_name: '',
  old_password: '',
  new_password: ''
})
const profileRules = {
  display_name: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  new_password: [
    {
      validator: (_rule, value, callback) => {
        if (value && value.length < 6) {
          callback(new Error('新密码至少 6 位'))
          return
        }
        if (value && !profileForm.old_password) {
          callback(new Error('请填写当前密码'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

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
  clearAvatarPending()
  avatarCropSourceUrl.value = ''
  try {
    const user = await uploadAvatarApi(file)
    if (user) {
      userStore.setUserInfo({ ...userStore.userInfo, ...user })
    }
    ElMessage.success('头像已更新')
  } catch (err) {
    ElMessage.error(err?.msg || err?.message || '头像上传失败')
  }
}

function onAvatarCropCancel() {
  clearAvatarPending()
  avatarCropSourceUrl.value = ''
}

function openProfileDialog() {
  profileForm.display_name = displayUserName.value
  profileForm.old_password = ''
  profileForm.new_password = ''
  profileVisible.value = true
}

function onUserMenuCommand(cmd) {
  if (cmd === 'profile') openProfileDialog()
  if (cmd === 'logout') handleLogout()
}

async function submitProfile() {
  if (!profileFormRef.value) return
  await profileFormRef.value.validate()
  profileSaving.value = true
  try {
    const payload = {
      display_name: profileForm.display_name.trim()
    }
    if (profileForm.new_password) {
      payload.old_password = profileForm.old_password
      payload.new_password = profileForm.new_password
    }
    const user = await updateProfileApi(payload)
    if (user) {
      userStore.setUserInfo({ ...userStore.userInfo, ...user })
    }
    ElMessage.success('资料已更新')
    profileVisible.value = false
  } catch (err) {
    ElMessage.error(err?.msg || err?.message || '保存失败')
  } finally {
    profileSaving.value = false
  }
}

const displayRole = computed(() => {
  const u = userStore.userInfo
  return u?.role_name || roleCodeToLabel(resolveRoleCode(u)) || '用户'
})

const menuVisibility = {
  '/dashboard': (role) => isAdminRole(role),
  '/chat': () => true,
  '/roles': (role) => isAdminRole(role),
  '/user-groups': (role) => isAdminRole(role),
  '/users': (role) => isAdminRole(role),
  '/models': (role) => isAdminRole(role),
  '/branding': () => true,
  '/knowledge-bases': (role) => isAdminRole(role),
  '/documents': (role) => isAdminRole(role),
  '/hit-test': () => true
}

const ADMIN_ONLY_PATHS = new Set([
  '/dashboard',
  '/roles',
  '/user-groups',
  '/users',
  '/models',
  '/knowledge-bases',
  '/documents'
])

const canSeeMenu = (path) => {
  const role = resolveRoleCode(userStore.userInfo)
  if (!role) return false
  const fn = menuVisibility[path]
  return fn ? fn(role) : false
}

/** 仅展示角标：不改变可见性逻辑 */
const isAdminOnlyPath = (path) => ADMIN_ONLY_PATHS.has(path)

/* 同步挂载暗色主题，避免首屏按钮先吃到亮色/默认 EP 样式导致各页观感不一致 */
document.documentElement.classList.add('admin-theme')
uiPrefs.applyColorMode(uiPrefs.colorMode, { admin: true })
brandingStore.applyBranding()

onMounted(async () => {
  document.documentElement.classList.add('admin-theme')
  uiPrefs.init()
  try {
    await userStore.ensureUserInfo()
  } catch (e) {
    /* ignore */
  }
  try {
    await brandingStore.fetchBranding()
  } catch (e) {
    brandingStore.applyBranding()
  }
  if (showSidebarStatus.value) {
    try {
      const data = await getStatsApi()
      sidebarServices.value = Array.isArray(data.services) ? data.services : []
    } catch (e) {
      sidebarServices.value = [
        { key: 'api', label: '后端 API', status: 'down', detail: '统计接口不可用' },
        { key: 'chroma', label: 'Chroma 向量服务', status: 'idle', detail: '未探测' },
        { key: 'bm25_cache', label: 'BM25 内存索引', status: 'idle', detail: '未探测' },
        { key: 'sqlite', label: '会话存储', status: 'idle', detail: '未探测' }
      ]
    }
  }
})

onUnmounted(() => {
  document.documentElement.classList.remove('admin-theme')
  uiPrefs.clearAdminColorMode()
})

const handleLogout = () => {
  document.documentElement.classList.remove('admin-theme')
  uiPrefs.clearAdminColorMode()
  userStore.logout()
}
</script>

<style scoped>
.layout-shell {
  position: relative;
  min-height: 100vh;
  overflow: visible;
  /* 透明，让 fixed 粒子成为唯一底；实黑由 body 承担 */
  background: transparent;
}

/* 系统概览：锁死视口高度，去掉底部多余可滚空白 */
.layout-shell--fill {
  height: 100dvh;
  max-height: 100dvh;
  min-height: 0;
  overflow: hidden;
}

/* —— 统一磨砂：仅 Aside（页眉不要毛玻璃；深蓝黑 30% + blur） —— */
.aside {
  background-color: rgba(10, 18, 36, 0.3);
  background-image: var(--admin-card-tint);
  border: 1px solid var(--glass-border);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  box-shadow: var(--glass-shadow);
}

.header {
  position: fixed !important;
  top: 0;
  left: 0;
  right: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: var(--admin-header-height);
  min-height: var(--admin-header-height);
  /* 左内边距与侧栏内容区一致 */
  padding: 0 24px 0 var(--admin-sidebar-pad-x);
  box-sizing: border-box;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
  -webkit-backdrop-filter: none;
  backdrop-filter: none;
}

.header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  height: 100%;
  /* 与 10 字系统名同宽 */
  width: calc(10 * var(--admin-brand-font-size));
  max-width: none;
  min-width: calc(10 * var(--admin-brand-font-size));
}

.header-title {
  margin: 0;
  width: 100%;
  font-size: var(--admin-brand-font-size);
  font-weight: var(--admin-fw-bold, 700);
  letter-spacing: 0;
  line-height: var(--admin-header-height);
  height: var(--admin-header-height);
  color: var(--admin-text);
  overflow: visible;
  text-overflow: clip;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  height: 100%;
}

.font-size-switch,
.color-mode-switch {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  gap: 2px;
  border-radius: 999px;
  background: var(--admin-fill);
  border: 1px solid var(--glass-divider);
}

.font-size-switch__btn,
.color-mode-switch__btn {
  min-width: 28px;
  height: 26px;
  padding: 0 8px;
  margin: 0;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--admin-text-muted);
  font-size: var(--admin-fs-caption);
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.font-size-switch__btn:hover,
.color-mode-switch__btn:hover {
  color: var(--admin-text);
}

.font-size-switch__btn.is-active,
.color-mode-switch__btn.is-active {
  background: color-mix(in srgb, var(--el-color-primary) 55%, transparent);
  color: #fff;
}

.user-chip {
  padding: 5px 11px;
  font-size: var(--admin-fs-caption);
  color: var(--admin-text);
  background: var(--admin-fill);
  border: 1px solid var(--glass-divider);
  border-radius: 999px;
}

.user-avatar-btn {
  padding: 0;
  margin: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  line-height: 0;
  border-radius: 50%;
  outline: none;
}

.user-avatar-btn:hover .user-avatar {
  box-shadow:
    0 0 0 2px color-mix(in srgb, var(--el-color-primary) 45%, transparent),
    0 0 12px color-mix(in srgb, var(--el-color-primary) 35%, transparent);
}

.avatar-file-input {
  display: none;
}

.user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  font-size: var(--admin-fs-body-lg);
  font-weight: 700;
  color: #fff;
  background: var(--el-color-primary);
  border: 2px solid color-mix(in srgb, var(--el-color-primary) 55%, rgba(255, 255, 255, 0.35));
  border-radius: 50%;
  flex-shrink: 0;
  object-fit: cover;
  box-sizing: border-box;
  transition: box-shadow 0.2s ease;
}

.user-avatar--img {
  padding: 0;
  background: rgba(255, 255, 255, 0.08);
}

.user-avatar--fallback {
  letter-spacing: 0;
  text-transform: none;
  user-select: none;
}

.profile-avatar-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.profile-avatar-btn .user-avatar {
  width: 56px;
  height: 56px;
  font-size: var(--admin-fs-title);
}

.layout-body {
  position: relative;
  z-index: 1;
  display: block;
  /* 顶栏贴顶无浮动间距；侧栏自 Header 下缘铺满到底 */
  padding: calc(var(--admin-header-height) + 12px) 12px 12px calc(var(--admin-sidebar-width) + 12px);
  min-width: 0;
  overflow: visible;
}

.layout-body--fill {
  height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
  box-sizing: border-box;
}

.aside {
  position: fixed !important;
  top: var(--admin-header-height);
  left: 0;
  bottom: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  width: var(--admin-sidebar-width);
  overflow: hidden;
  /* 左贴边直角；右上/右下 14px 与数据卡片一致 */
  border-radius: 0 14px 14px 0;
  border-left: none;
  color: var(--admin-text);
}

.aside-brand {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  padding: 16px 16px 10px;
  font-size: var(--admin-fs-caption);
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--admin-text-muted);
}

.menu {
  position: relative;
  z-index: 1;
  flex: 0 1 auto;
  min-height: 0;
  padding: 4px 8px 8px;
  overflow-y: auto;
  border-right: none;
  background: transparent;
}

.aside-status {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  padding: 0 14px 4px;
}

.aside-spacer {
  flex: 1 1 auto;
  min-height: 8px;
}

.aside-footer {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  padding: 8px 14px 14px;
  font-size: 11px;
  line-height: 1.45;
  letter-spacing: 0.02em;
  color: var(--admin-text-dim);
  text-align: center;
}

.aside-status__divider {
  height: 1px;
  margin: 4px 2px 14px;
  background: var(--glass-divider);
}

.aside-status__title {
  margin-bottom: 12px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--admin-text-dim);
}

.aside-status__item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.aside-status__item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.aside-status__item + .aside-status__item {
  margin-top: 12px;
}

.aside-status__dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: #8c8c8c;
}

.aside-status__dot.is-ok {
  background: #52c41a;
  box-shadow: 0 0 0 4px rgba(82, 196, 26, 0.16);
}

.aside-status__dot.is-idle {
  background: #faad14;
  box-shadow: 0 0 0 4px rgba(250, 173, 20, 0.16);
}

.aside-status__dot.is-down,
.aside-status__dot.is-warn {
  background: #f56c6c;
  box-shadow: 0 0 0 4px rgba(245, 108, 108, 0.16);
}

.aside-status__body {
  flex: 1;
  min-width: 0;
}

.aside-status__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: var(--admin-fs-caption);
  color: var(--admin-text);
}

.aside-status__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.aside-status__tag {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--admin-text-muted);
}

.aside-status__tag.is-ok {
  color: #52c41a;
}

.aside-status__tag.is-idle {
  color: #faad14;
}

.aside-status__tag.is-down,
.aside-status__tag.is-warn {
  color: #f56c6c;
}

.aside-status__detail {
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.35;
  color: var(--admin-text-dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.el-menu) {
  background: transparent;
  border-right: none;
}

:deep(.el-menu-item) {
  display: flex;
  align-items: center;
  height: 42px;
  margin: 2px 0;
  padding: 0 12px !important;
  border-radius: 0;
  border-bottom: 2px solid transparent;
  color: var(--admin-text-muted);
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

:deep(.el-menu-item .el-icon) {
  margin-right: 8px;
  color: var(--admin-text-muted);
}

:deep(.el-menu-item .menu-label) {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.el-menu-item:hover) {
  background: var(--admin-menu-hover-bg);
  color: var(--admin-menu-hover-text);
}

:deep(.el-menu-item.is-active) {
  background: transparent !important;
  color: var(--admin-menu-active-text);
  box-shadow: none !important;
  border-bottom-color: var(--el-color-primary);
}

:deep(.el-menu-item:hover .el-icon) {
  color: var(--admin-menu-hover-text);
}

:deep(.el-menu-item.is-active .el-icon) {
  color: var(--admin-menu-active-icon);
}

:deep(.el-menu-item.is-active .menu-label) {
  color: var(--admin-menu-active-text);
  font-weight: 600;
}

.admin-badge {
  flex-shrink: 0;
  margin-left: 8px;
  padding: 2px 7px;
  font-size: 10px;
  line-height: 1.4;
  letter-spacing: 0.04em;
  color: var(--admin-badge-text);
  background: var(--admin-badge-bg);
  border: 1px solid var(--glass-divider);
  border-radius: 999px;
}

.main {
  position: relative;
  z-index: 1;
  min-width: 0;
  padding: 0 8px 24px 4px;
  background: transparent;
  overflow: visible;
}

/* 概览页：去掉 .main 底部 24px 留白（其他页仍保留便于滚动） */
.main--fill {
  height: 100%;
  min-height: 0;
  padding-bottom: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.main--fill > * {
  flex: 1;
  min-height: 0;
}

@media (max-width: 992px) {
  .layout-shell--fill {
    height: auto;
    max-height: none;
    min-height: 100dvh;
    overflow: visible;
  }

  .layout-body--fill {
    height: auto;
    max-height: none;
    overflow: visible;
  }

  .main--fill {
    height: auto;
    overflow: visible;
    display: block;
  }

  .main--fill > * {
    flex: none;
    min-height: 0;
  }
}
</style>

<style>
/* 头像下拉（teleport） */
.user-menu-popper.el-dropdown__popper,
.user-menu-popper {
  background: var(--glass-fill) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--glass-radius) !important;
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  box-shadow: var(--glass-shadow) !important;
  padding: 4px !important;
}

.user-menu-popper .el-dropdown-menu {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}

.user-menu-popper .el-dropdown-menu__item {
  color: rgba(230, 235, 245, 0.88) !important;
  border-radius: 8px;
}

.user-menu-popper .el-dropdown-menu__item:not(.is-disabled):hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #fff !important;
}

.user-menu-popper .user-menu-meta {
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
  gap: 2px;
  height: auto !important;
  line-height: 1.35 !important;
  cursor: default !important;
  opacity: 1 !important;
  color: rgba(200, 210, 230, 0.75) !important;
}

.user-menu-popper .user-menu-meta__name {
  font-size: var(--admin-fs-body);
  font-weight: 600;
  color: #fff;
}

.user-menu-popper .user-menu-meta__account {
  font-size: var(--admin-fs-caption);
  color: rgba(180, 190, 210, 0.55);
}
</style>
