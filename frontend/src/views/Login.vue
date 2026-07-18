<template>
  <div class="login-page" @click="onLoginPageClick">
    <!-- 全屏流体点阵氛围底；鼠标邻近仅做提亮聚焦，不改波场结构 -->
    <EnvParticleField :pause-pointer-focus="showLoginModal" />

    <!-- 顶栏：各导航项下方独立下拉（对齐参考：对应区域展示） -->
    <header class="login-nav" @click.stop>
      <div class="provider-brand" aria-label="提供方品牌">
        <span class="provider-mark" aria-hidden="true">
          <i></i><i></i><i></i>
        </span>
        <span class="provider-name">{{ PROVIDER_NAME }}</span>
      </div>

      <nav class="decor-nav" aria-label="装饰导航">
        <div
          v-for="item in decorNav"
          :key="item.key"
          class="nav-item"
          :class="{ 'is-open': megaOpen && activeMegaKey === item.key }"
        >
          <button
            type="button"
            class="decor-link"
            :class="{ active: megaOpen && activeMegaKey === item.key }"
            :aria-expanded="megaOpen && activeMegaKey === item.key"
            @click.stop="onDecorNavClick(item.key)"
          >
            {{ item.label }}
          </button>
          <Transition name="nav-dropdown">
            <div
              v-if="megaOpen && activeMegaKey === item.key"
              class="nav-dropdown"
              role="menu"
            >
              <div class="nav-dropdown__card">
                <ul class="nav-dropdown__list">
                  <li v-for="(link, idx) in item.links" :key="idx">
                    <button
                      type="button"
                      class="nav-dropdown__link"
                      :class="{ active: activeMegaLink === link }"
                      role="menuitem"
                      @click.stop="onMegaLinkClick(link)"
                    >
                      {{ link }}
                    </button>
                  </li>
                </ul>
              </div>
            </div>
          </Transition>
        </div>
      </nav>

      <button type="button" class="sign-in-trigger" @click.stop="openLoginModal">
        SIGN IN
      </button>
    </header>

    <!-- 主视觉：徽章 → 双行标题 → 单颗胶囊 CTA -->
    <main class="login-hero">
      <div class="status-pill">
        <span class="status-dot"></span>
        <span>{{ STATUS_LABEL }}</span>
      </div>
      <h1 class="hero-title">
        <span class="hero-brand">{{ brandingStore.brandName }}</span>
        <span class="hero-tagline">{{ HERO_TAGLINE }}</span>
      </h1>
      <div class="cta-enter-wrap" :class="{ 'is-pressed': ctaPressed }">
        <button
          type="button"
          class="cta-enter"
          @click.stop="openLoginModal"
          @mousedown="ctaPressed = true"
          @mouseup="ctaPressed = false"
          @mouseleave="ctaPressed = false"
          :class="{ 'is-pressed': ctaPressed }"
        >
          <span class="cta-enter__label">ENTER</span>
        </button>
      </div>
    </main>

    <p class="login-footer">{{ PROVIDER_FOOTER }}</p>

    <!-- 登录浮窗 -->
    <Teleport to="body">
      <Transition name="login-modal">
        <div
          v-if="showLoginModal"
          class="login-modal-mask"
          @click.self="closeLoginModal"
        >
          <div
            class="login-modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="login-modal-title"
            @keydown.esc.prevent="closeLoginModal"
          >
            <span class="pointer-edge-glow" aria-hidden="true" />
            <button type="button" class="modal-close" aria-label="关闭" @click="closeLoginModal">
              ×
            </button>

            <div class="login-header">
              <div class="logo-frame">
                <img
                  v-if="brandingStore.brandLogoUrl && !logoBroken"
                  :src="brandingStore.brandLogoUrl"
                  alt="logo"
                  class="logo-img"
                  @error="onLogoError"
                />
                <div v-else class="logo-fallback" aria-hidden="true"></div>
              </div>
              <h2 id="login-modal-title">欢迎使用</h2>
              <p class="login-header__sub">
                {{ brandingStore.brandLoginTitle || '登录您的账户' }}
              </p>
            </div>

            <div class="login-tabs" role="tablist">
              <button
                type="button"
                class="tab-item"
                role="tab"
                :aria-selected="loginType === 'employee'"
                :class="{ active: loginType === 'employee' }"
                @click="switchLoginType('employee')"
              >
                员工登录
              </button>
              <button
                type="button"
                class="tab-item"
                role="tab"
                :aria-selected="loginType === 'admin'"
                :class="{ active: loginType === 'admin' }"
                @click="switchLoginType('admin')"
              >
                管理员登录
              </button>
            </div>

            <el-form
              :model="form"
              :rules="rules"
              ref="formRef"
              class="login-form"
              label-position="top"
              :hide-required-asterisk="true"
              @submit.prevent
            >
              <el-form-item prop="username" label="用户名" class="login-field">
                <el-input
                  v-model="form.username"
                  placeholder="请输入用户名"
                  prefix-icon="User"
                  size="large"
                  @keyup.enter="handleLogin"
                  @input="loginError = ''"
                />
              </el-form-item>

              <el-form-item prop="password" label="密码" class="login-field login-field--password">
                <el-input
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="请输入密码"
                  prefix-icon="Lock"
                  size="large"
                  @keyup.enter="handleLogin"
                  @input="loginError = ''"
                >
                  <template #suffix>
                    <button
                      type="button"
                      class="pwd-eye"
                      :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                      @click.stop="showPassword = !showPassword"
                    >
                      <el-icon :size="18">
                        <View v-if="showPassword" />
                        <Hide v-else />
                      </el-icon>
                    </button>
                  </template>
                </el-input>
              </el-form-item>

              <!-- 同一行：左错误提示 · 右忘记密码（对齐参考图） -->
              <div class="login-pwd-row">
                <p
                  class="login-error"
                  :class="{ 'is-placeholder': !loginError }"
                  role="alert"
                  aria-live="polite"
                >
                  {{ loginError || '用户名或密码错误，请重新输入' }}
                </p>
                <button type="button" class="login-aux-link" @click="onForgotPassword">
                  忘记密码？
                </button>
              </div>

              <el-form-item class="login-field--submit">
                <el-button
                  type="primary"
                  class="login-btn"
                  size="large"
                  :loading="loading"
                  @click="handleLogin"
                >
                  登录
                </el-button>
              </el-form-item>
            </el-form>

            <p class="login-footer-aux">
              没有账号？
              <button type="button" class="login-aux-link" @click="onApplyAuth">申请授权</button>
            </p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBrandingStore } from '@/stores/branding'
import { loginApi } from '@/api/auth'
import { isAdminRole } from '@/utils/role'
import { ElMessage } from 'element-plus'
import { View, Hide } from '@element-plus/icons-vue'
import EnvParticleField from '@/components/EnvParticleField.vue'
import { useGlassPointerGlow } from '@/composables/useGlassPointerGlow'
import '@/styles/login.css'

useGlassPointerGlow()

/** 提供方品牌（管理员白标改不了） */
const PROVIDER_NAME = '六朵云'
/** 登录页底部弱展示：固定提供方署名（不读 brand_footer_text） */
const PROVIDER_FOOTER = 'Powered by 六朵云 · RAG Platform'
const STATUS_LABEL = '知识即服务'
const HERO_TAGLINE = '让企业知识即问即答'

/** Mega Menu 多栏模块（占位文案，后续可改） */
const decorNav = [
  {
    key: 'about',
    label: '关于我们',
    title: '关于六朵云',
    links: ['平台愿景', '技术理念', '交付能力', '白标定制']
  },
  {
    key: 'service',
    label: '知识服务',
    title: '知识服务',
    links: ['知识库管理', '文档智能检索', '企业级问答', '命中率验证']
  },
  {
    key: 'support',
    label: '服务支持',
    title: '服务支持',
    links: ['部署上线', '权限与角色', '运维保障', '授权申请']
  },
  {
    key: 'contact',
    label: '联系我们',
    title: '联系我们',
    links: ['商务合作', '技术支持', '演示预约', '工作时间']
  }
]

const router = useRouter()
const userStore = useUserStore()
const brandingStore = useBrandingStore()
const formRef = ref(null)
const loading = ref(false)
const loginType = ref('employee')
const logoBroken = ref(false)
const showLoginModal = ref(false)
const loginError = ref('')
const showPassword = ref(false)
const ctaPressed = ref(false)
const megaOpen = ref(false)
const activeMegaKey = ref('about')
const activeMegaLink = ref('')

/** 弹窗 z-index=3000，Message 需更高才能看见 */
function toastInModal(message, type = 'error') {
  ElMessage({
    message,
    type,
    zIndex: 4000,
    duration: 3200,
    appendTo: document.body
  })
}

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

function switchLoginType(type) {
  loginType.value = type
}

function onLogoError() {
  logoBroken.value = true
}

watch(
  () => brandingStore.brandLogoUrl,
  () => {
    logoBroken.value = false
  }
)

function closeMegaMenu() {
  megaOpen.value = false
  activeMegaLink.value = ''
}

function onDecorNavClick(key) {
  if (showLoginModal.value) closeLoginModal()
  // 仅点击唤起：同项再点收起，异项切换栏目
  if (megaOpen.value && activeMegaKey.value === key) {
    closeMegaMenu()
    return
  }
  activeMegaKey.value = key
  activeMegaLink.value = ''
  megaOpen.value = true
}

function onLoginPageClick() {
  if (megaOpen.value) closeMegaMenu()
}

function onMegaLinkClick(link) {
  activeMegaLink.value = link
  ElMessage({
    message: `「${link}」为占位入口，后续可替换为正式内容`,
    type: 'info',
    zIndex: 4000,
    duration: 2200
  })
}

function onForgotPassword() {
  ElMessage({ message: '请联系管理员重置密码', type: 'info', zIndex: 4000, duration: 2800 })
}

function onApplyAuth() {
  ElMessage({ message: '请联系管理员申请授权', type: 'info', zIndex: 4000, duration: 2800 })
}

async function openLoginModal() {
  closeMegaMenu()
  loginError.value = ''
  showLoginModal.value = true
  await nextTick()
  document.body.style.overflow = 'hidden'
}

function closeLoginModal() {
  showLoginModal.value = false
  showPassword.value = false
  loginError.value = ''
  document.body.style.overflow = ''
}

function onKeydown(e) {
  if (e.key !== 'Escape') return
  if (showLoginModal.value) {
    closeLoginModal()
    return
  }
  if (megaOpen.value) closeMegaMenu()
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  try {
    await brandingStore.fetchBranding()
    brandingStore.applyBranding()
  } catch (e) {
    brandingStore.applyBranding()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})

const handleLogin = async () => {
  if (!formRef.value) return
  loginError.value = ''
  await formRef.value.validate()
  loading.value = true
  try {
    const data = await loginApi(form)
    userStore.setToken(data.token)
    userStore.setUserInfo(data.user)

    const role = data.user.role

    if (loginType.value === 'admin' && !isAdminRole(role)) {
      const tip = '当前账号无管理员权限，请使用员工登录'
      loginError.value = tip
      toastInModal(tip, 'error')
      userStore.setSession('', null)
      return
    }

    toastInModal('登录成功', 'success')
    closeLoginModal()
    const redirectPath = isAdminRole(role) ? '/dashboard' : '/chat'
    router.push(redirectPath)
  } catch (error) {
    const msg =
      error?.message ||
      error?.msg ||
      error?.response?.data?.msg ||
      '用户名或密码错误，请重新输入'
    const tip = /用户名|密码|认证|unauthorized|401/i.test(String(msg))
      ? '用户名或密码错误，请重新输入'
      : msg
    loginError.value = tip
    toastInModal(tip, 'error')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: #000000;
  color: var(--login-text);
  font-family: var(--login-font-sans);
}

.login-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 25;
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(420px, 2.2fr) minmax(120px, 1fr);
  align-items: center;
  gap: 16px;
  padding: 22px 48px;
  background: linear-gradient(to bottom, rgba(5, 5, 5, 0.72), rgba(5, 5, 5, 0));
  pointer-events: none;
}

.login-nav > * {
  pointer-events: auto;
}

.provider-brand {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  justify-self: start;
}

.provider-mark {
  position: relative;
  width: 40px;
  height: 40px;
  display: inline-block;
  flex-shrink: 0;
}

.provider-mark i {
  position: absolute;
  width: 12px;
  height: 12px;
  background: var(--login-text);
  border-radius: 1px;
}

.provider-mark i:nth-child(1) { left: 0; bottom: 0; }
.provider-mark i:nth-child(2) { left: 14px; bottom: 14px; }
.provider-mark i:nth-child(3) { left: 28px; top: 0; }

.provider-name {
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--login-text);
  white-space: nowrap;
}

.decor-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px 28px;
  justify-self: center;
  width: min(640px, 56vw);
}

.nav-item {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
}

.decor-link {
  position: relative;
  z-index: 32;
  appearance: none;
  border: 0;
  background: transparent;
  padding: 8px 2px;
  cursor: pointer;
  color: var(--login-text-muted);
  font-size: 16px;
  font-weight: 400;
  letter-spacing: 0.16em;
  white-space: nowrap;
  transition: color 0.28s ease, box-shadow 0.28s ease, filter 0.28s ease;
  box-shadow: inset 0 -1px 0 transparent;
}

.decor-link:hover {
  color: var(--login-nav-hover);
  filter: brightness(1.12);
  box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.55);
}

/* 展开时：白字 + 与卡片一致的蓝色下划线，标题落入卡片顶部 */
.decor-link.active,
.nav-item.is-open .decor-link:hover {
  color: #fff;
  filter: none;
  box-shadow: inset 0 -1px 0 var(--el-color-primary);
}

.decor-link:active {
  color: var(--login-text-dim);
  filter: brightness(0.9);
  transition-duration: 0.12s;
}

/* 卡片上扩覆盖导航标题区域，并相对导航居中 */
.nav-dropdown {
  position: absolute;
  top: 0;
  left: 50%;
  z-index: 31;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: max-content;
  min-width: 220px;
  text-align: center;
  transform: translateX(-50%);
  pointer-events: none;
}

.nav-dropdown__card {
  width: 100%;
  min-width: 220px;
  /* 顶部留白叠在导航标题下，形成“卡片覆盖副标题” */
  padding: 44px 14px 14px;
  border-radius: 16px;
  border: 1px solid rgba(120, 155, 220, 0.36);
  background: linear-gradient(
    180deg,
    rgba(8, 10, 18, 0.9) 0%,
    rgba(12, 16, 28, 0.8) 55%,
    rgba(18, 30, 52, 0.74) 100%
  );
  -webkit-backdrop-filter: blur(16px) saturate(1.08);
  backdrop-filter: blur(16px) saturate(1.08);
  box-shadow:
    0 18px 40px rgba(0, 0, 0, 0.42),
    0 0 0 1px rgba(140, 170, 230, 0.1),
    inset 0 0 0 1px rgba(160, 185, 230, 0.08);
  pointer-events: auto;
}

.nav-dropdown__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.nav-dropdown__link {
  appearance: none;
  border: 0;
  background: transparent;
  width: auto;
  max-width: 100%;
  text-align: center;
  padding: 8px 4px;
  border-radius: 0;
  cursor: pointer;
  color: rgba(190, 194, 208, 0.78);
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.08em;
  line-height: 1.4;
  white-space: nowrap;
  transition: color 0.28s ease, box-shadow 0.28s ease;
  box-shadow: inset 0 -1px 0 transparent;
}

/* 子选项：与导航一致的蓝色下划线，无方框底 */
.nav-dropdown__link:hover,
.nav-dropdown__link.active {
  color: #fff;
  background: transparent;
  box-shadow: inset 0 -1px 0 var(--el-color-primary);
}

.nav-dropdown__link:active {
  color: rgba(220, 224, 235, 0.85);
  transition-duration: 0.12s;
}

.nav-dropdown-enter-active,
.nav-dropdown-leave-active {
  transition:
    opacity 0.22s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.24s cubic-bezier(0.22, 1, 0.36, 1);
}

.nav-dropdown-enter-from,
.nav-dropdown-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-6px);
}

.sign-in-trigger {
  justify-self: end;
  appearance: none;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: var(--el-color-primary);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.2em;
  white-space: nowrap;
  transition: color 0.28s ease, filter 0.28s ease, box-shadow 0.28s ease, opacity 0.28s ease;
  box-shadow: inset 0 -1px 0 transparent;
}

.sign-in-trigger:hover {
  color: var(--el-color-primary-light-3, var(--el-color-primary));
  filter: brightness(1.18);
  box-shadow: inset 0 -1px 0 var(--el-color-primary);
}

.sign-in-trigger:active {
  filter: brightness(0.88);
  opacity: 0.9;
  transition-duration: 0.12s;
}

.login-hero {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 96px 24px 80px;
  text-align: center;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  margin-bottom: 36px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(200, 204, 216, 0.72);
  font-size: 14px;
  letter-spacing: 0.06em;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--el-color-primary);
  box-shadow: 0 0 10px var(--login-glow);
}

.hero-title {
  margin: 0;
  max-width: 960px;
  font-family: var(--login-font-sans);
  font-weight: 600;
  line-height: 1.22;
  letter-spacing: -0.02em;
  color: var(--login-text);
}

.hero-brand {
  display: block;
  font-size: clamp(56px, 8.2vw, 92px);
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.hero-tagline {
  display: block;
  margin-top: 0.28em;
  font-size: clamp(48px, 7.4vw, 80px);
  font-weight: 500;
  font-style: normal;
  letter-spacing: -0.02em;
  color: rgba(170, 174, 188, 0.72);
  line-height: 1.25;
}

/* ENTER：单颗胶囊形（对齐参考 CTA 形制） */
.cta-enter-wrap {
  position: relative;
  display: inline-flex;
  margin-top: 64px;
  transition: transform 0.28s ease, filter 0.28s ease;
}

.cta-enter-wrap:hover {
  transform: scale(1.03);
}

.cta-enter-wrap.is-pressed,
.cta-enter-wrap:has(.cta-enter:active) {
  transform: scale(0.97);
  filter: brightness(0.96);
  transition-duration: 0.12s;
}

.cta-enter {
  position: relative;
  appearance: none;
  border: 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 220px;
  padding: 22px 56px;
  border-radius: 999px;
  color: #0a0a0a;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.14em;
  background: #fff;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.08),
    0 10px 28px rgba(0, 0, 0, 0.35),
    0 0 24px rgba(255, 255, 255, 0.12);
  transition:
    background 0.28s ease,
    box-shadow 0.28s ease,
    letter-spacing 0.28s ease;
  animation: cta-breathe 2.6s ease-in-out infinite;
}

.cta-enter__label {
  position: relative;
  z-index: 1;
  line-height: 1;
}

.cta-enter-wrap:hover .cta-enter {
  background: #f4f4f5;
  animation-duration: 1.9s;
}

.cta-enter-wrap:hover .cta-enter__label {
  letter-spacing: 0.16em;
}

.cta-enter:active .cta-enter__label,
.cta-enter.is-pressed .cta-enter__label {
  letter-spacing: 0.1em;
}

@keyframes cta-breathe {
  0%, 100% {
    box-shadow:
      0 0 0 1px rgba(255, 255, 255, 0.06),
      0 10px 28px rgba(0, 0, 0, 0.35),
      0 0 16px rgba(255, 255, 255, 0.08);
  }
  50% {
    box-shadow:
      0 0 0 1px rgba(255, 255, 255, 0.14),
      0 12px 32px rgba(0, 0, 0, 0.38),
      0 0 36px rgba(255, 255, 255, 0.22),
      0 0 56px color-mix(in srgb, var(--el-color-primary) 22%, transparent);
  }
}

.login-footer {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 18px;
  z-index: 2;
  margin: 0;
  text-align: center;
  font-size: 14px;
  color: var(--login-text-dim);
  letter-spacing: 0.06em;
  line-height: 1.6;
  pointer-events: none;
}

/* —— 登录弹窗：分层雾化毛玻璃（对齐参考） —— */
.login-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  /* 轻遮罩 + 中等模糊，粒子柔和透出 */
  background: var(--glass-mask);
  -webkit-backdrop-filter: blur(var(--glass-mask-blur));
  backdrop-filter: blur(var(--glass-mask-blur));
}

.login-modal-card {
  position: relative;
  width: min(520px, 100%);
  overflow: hidden;
  border-radius: 24px;
  color: var(--login-text);
  /* 登录浮窗独立配方，不受后台日历风 --glass-* 影响 */
  --glass-glow: 0;
  --glow-x: 50%;
  --glow-y: 50%;
  --glow-r: 140px;
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

/* 鼠标邻近描边照亮（独立层，不占用 ::before/::after 薄雾） */
.login-modal-card .pointer-edge-glow {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  border-radius: inherit;
  padding: 1px;
  pointer-events: none;
  opacity: var(--glass-glow, 0);
  background: radial-gradient(
    var(--glow-r, 140px) circle at var(--glow-x, 50%) var(--glow-y, 50%),
    color-mix(in srgb, var(--el-color-primary) 90%, #fff 10%) 0%,
    color-mix(in srgb, var(--el-color-primary) 45%, transparent) 38%,
    transparent 68%
  );
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask-composite: exclude;
}

/* 细腻均匀薄雾磨砂（哑光细砂，克制） */
.login-modal-card::before {
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

/* 下半柔雾蓝层叠（中饱和） */
.login-modal-card::after {
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

.login-modal-card > * {
  position: relative;
  z-index: 1;
}

.modal-close {
  position: absolute;
  top: 10px;
  right: 14px;
  z-index: 3;
  border: 0;
  background: transparent;
  color: var(--login-text-muted);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  transition: color 0.2s ease;
}

.modal-close:hover {
  color: var(--login-text);
}

.login-tabs {
  display: flex;
  margin: 0 40px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.tab-item {
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

.tab-item:hover {
  color: var(--login-text);
}

.tab-item.active {
  color: #fff;
  font-weight: 600;
  background: color-mix(in srgb, var(--el-color-primary) 28%, transparent);
  box-shadow: none;
}

.login-header {
  padding: 32px 48px 18px;
  text-align: center;
}

.logo-frame {
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
  border-radius: 14px;
  overflow: hidden;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

.logo-fallback {
  width: 100%;
  height: 100%;
  border-radius: 0;
  background: linear-gradient(
    135deg,
    var(--el-color-primary-light-3, var(--el-color-primary)),
    var(--el-color-primary)
  );
  box-shadow: none;
}

.login-header h2 {
  margin: 0 0 8px;
  font-family: var(--login-font-sans);
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 0.03em;
  line-height: 1.3;
  color: var(--login-text);
}

.login-header__sub {
  margin: 0;
  color: rgba(200, 200, 205, 0.55);
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
}

.login-form {
  padding: 22px 48px 12px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.login-form :deep(.el-form-item__label) {
  color: rgba(235, 235, 240, 0.88);
  font-size: 15px;
  font-weight: 600;
  padding-bottom: 8px;
  line-height: 1.35;
}

.login-field-head {
  display: none;
}

.login-field-label {
  color: rgba(235, 235, 240, 0.88);
  font-size: 15px;
  font-weight: 600;
}

.login-field--password {
  margin-bottom: 14px;
}

.login-pwd-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 2px 0 20px;
  min-height: 28px;
  padding: 4px 0 2px;
}

.login-pwd-row .login-error {
  flex: 1;
  min-width: 0;
  margin: 0;
  min-height: 22px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #f89898;
  font-size: 14px;
  line-height: 1.75;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.login-pwd-row .login-error.is-placeholder {
  color: transparent;
  user-select: none;
  pointer-events: none;
}

.login-pwd-row .login-aux-link {
  flex-shrink: 0;
  appearance: none;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
  color: rgba(180, 180, 190, 0.42);
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.02em;
  transition: color 0.2s ease;
}

.login-pwd-row .login-aux-link:hover {
  color: rgba(210, 210, 220, 0.62);
}

.login-aux-link {
  appearance: none;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
  color: rgba(180, 180, 190, 0.42);
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.02em;
  transition: color 0.2s ease;
}

.login-aux-link:hover {
  color: rgba(210, 210, 220, 0.62);
}

.login-form :deep(.el-input__wrapper) {
  min-height: 54px;
  border-radius: 12px;
  background: rgba(6, 8, 14, 0.55);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset;
  backdrop-filter: blur(6px);
}

.login-form :deep(.el-input__wrapper:hover),
.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--el-color-primary) 55%, transparent) inset;
}

.login-form :deep(.el-input__inner) {
  color: var(--login-text);
  font-size: 17px;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: var(--login-text-dim);
}

.login-form :deep(.el-input__prefix),
.login-form :deep(.el-input__suffix) {
  color: var(--login-text-muted);
}

/* 密码小眼睛常驻：闭眼=隐藏，睁眼=显示 */
.pwd-eye {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  appearance: none;
  border: 0;
  background: transparent;
  padding: 0 4px;
  margin: 0;
  cursor: pointer;
  color: rgba(200, 200, 210, 0.62);
  transition: color 0.2s ease;
}

.pwd-eye:hover {
  color: rgba(235, 235, 240, 0.92);
}

/* 兜底隐藏必填星号 */
.login-form :deep(.el-form-item.is-required:not(.is-no-asterisk) > .el-form-item__label::before),
.login-form :deep(.el-form-item.is-required:not(.is-no-asterisk) .el-form-item__label-wrap > .el-form-item__label::before) {
  display: none !important;
  content: none !important;
}

.login-field--submit {
  margin-top: 8px;
  margin-bottom: 8px;
}

.login-btn {
  width: 100%;
  height: 56px;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.14em;
  border-radius: 12px;
  border: 0;
  background: rgba(255, 255, 255, 0.14) !important;
  color: #fff !important;
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset;
}

.login-btn:hover,
.login-btn:focus {
  background: rgba(255, 255, 255, 0.2) !important;
  color: #fff !important;
}

.login-footer-aux {
  margin: 0;
  padding: 8px 48px 36px;
  text-align: center;
  font-size: 14px;
  line-height: 1.65;
  color: rgba(180, 180, 190, 0.38);
}

.login-footer-aux .login-aux-link {
  margin-left: 4px;
}

.login-modal-enter-active,
.login-modal-leave-active {
  transition: opacity 0.28s ease;
}

.login-modal-enter-active .login-modal-card,
.login-modal-leave-active .login-modal-card {
  transition: transform 0.28s ease, opacity 0.28s ease;
}

.login-modal-enter-from,
.login-modal-leave-to {
  opacity: 0;
}

.login-modal-enter-from .login-modal-card,
.login-modal-leave-to .login-modal-card {
  opacity: 0;
  transform: scale(0.94) translateY(8px);
}

@media (max-width: 900px) {
  .login-nav {
    grid-template-columns: auto 1fr auto;
    padding: 16px 20px;
  }

  .decor-nav {
    width: min(100%, 420px);
    gap: 6px 12px;
  }

  .decor-link {
    font-size: 14px;
    letter-spacing: 0.1em;
  }

  .provider-mark {
    width: 30px;
    height: 30px;
  }

  .provider-mark i {
    width: 9px;
    height: 9px;
  }

  .provider-mark i:nth-child(2) { left: 10px; bottom: 10px; }
  .provider-mark i:nth-child(3) { left: 20px; top: 0; }

  .provider-name {
    font-size: 22px;
  }

  .sign-in-trigger {
    font-size: 15px;
    letter-spacing: 0.16em;
  }

  .login-nav {
    padding: 16px 20px;
  }

  .nav-dropdown {
    min-width: 168px;
  }

  .hero-title {
    padding: 0 8px;
  }
}

@media (max-width: 640px) {
  .login-nav {
    grid-template-columns: 1fr auto;
    row-gap: 12px;
  }

  .decor-nav {
    grid-column: 1 / -1;
    order: 3;
    width: 100%;
    justify-content: space-between;
  }

  .sign-in-trigger {
    grid-column: 2;
    grid-row: 1;
  }

}
</style>
