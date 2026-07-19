<template>
  <div class="dashboard page-shell dashboard--fill" v-loading="loading">
    <div class="page-header">
      <h2>系统概览</h2>
      <div class="header-badge" :class="{ 'is-stale': !statsReady }">
        <span class="pulse" />
        {{ statsReady ? `实时更新 ${clockTime}` : '加载中' }}
      </div>
    </div>

    <div class="page-body dash-body">
      <!-- 1. 核心 KPI -->
      <el-row :gutter="12" class="stat-grid">
        <el-col v-for="card in statCards" :key="card.key" :xs="12" :sm="8" :lg="4">
          <el-card class="stat-card" shadow="never" :style="{ '--card-color': card.color }">
            <div class="stat-main">
              <div class="stat-icon">{{ card.icon }}</div>
              <div class="stat-info">
                <div class="stat-value">{{ card.value }}</div>
                <div class="stat-label">{{ card.label }}</div>
              </div>
            </div>
            <div class="stat-footer">
              <span>{{ card.desc }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 2. 左：对话运营 + 资产分布；右：时间 / 快捷 -->
      <el-row :gutter="12" class="chart-grid">
        <el-col :xs="24" :lg="14" class="chart-col">
          <div class="main-stack">
            <el-card class="chart-card chart-card--fill chart-card--center chat-card" shadow="never">
              <div class="card-title">
                <div>
                  <h3>对话运营</h3>
                </div>
              </div>
              <div class="bar-chart">
                <div
                  v-for="m in chatBarMetrics"
                  :key="m.label"
                  class="bar-item"
                  :style="{ '--bar-color': m.color }"
                >
                  <div class="bar-value">{{ m.value }}</div>
                  <div class="bar-track">
                    <div class="bar-fill" :style="{ height: m.pct + '%' }" />
                  </div>
                  <div class="bar-label">{{ m.label }}</div>
                </div>
              </div>
            </el-card>

            <el-card class="chart-card chart-card--fill chart-card--center asset-card" shadow="never">
              <div class="card-title">
                <div>
                  <h3>资产分布</h3>
                </div>
              </div>
              <div class="dist-grid">
                <div class="dist-block">
                  <div class="dist-block__title">文档状态</div>
                  <div v-if="statusBars.length" class="dist-bars">
                    <div v-for="item in statusBars" :key="item.key" class="dist-row">
                      <span class="dist-row__label">{{ item.label }}</span>
                      <div class="dist-row__track">
                        <div
                          class="dist-row__fill"
                          :style="{ width: item.pct + '%', background: item.color }"
                        />
                      </div>
                      <span class="dist-row__value">{{ item.value }}</span>
                    </div>
                  </div>
                  <p v-else class="empty-tip">暂无文档</p>
                </div>
                <div class="dist-block">
                  <div class="dist-block__title">文件格式</div>
                  <div v-if="typeBars.length" class="dist-bars">
                    <div v-for="item in typeBars" :key="item.key" class="dist-row">
                      <span class="dist-row__label">{{ item.label }}</span>
                      <div class="dist-row__track">
                        <div
                          class="dist-row__fill"
                          :style="{ width: item.pct + '%', background: item.color }"
                        />
                      </div>
                      <span class="dist-row__value">{{ item.value }}</span>
                    </div>
                  </div>
                  <p v-else class="empty-tip">暂无格式数据</p>
                </div>
              </div>
              <div class="dist-meta">
                <span>今日新增文档 <strong>{{ stats.today_new_docs }}</strong></span>
                <span>单库平均切片 <strong>{{ stats.avg_chunks_per_kb }}</strong></span>
              </div>
            </el-card>
          </div>
        </el-col>

        <el-col :xs="24" :lg="10" class="chart-col">
          <div class="side-stack">
            <el-card class="chart-card time-card" shadow="never">
              <div class="time-card__label">系统时间</div>
              <div class="time-card__clock">{{ clockTime }}</div>
              <div class="time-card__date">{{ clockDate }}</div>
              <div class="time-card__meta">
                <div class="time-meta-box">
                  <span class="time-meta-box__label">本页停留</span>
                  <strong class="time-meta-box__value">{{ stayText }}</strong>
                </div>
                <div class="time-meta-box">
                  <span class="time-meta-box__label">时区</span>
                  <strong class="time-meta-box__value">{{ timeZoneText }}</strong>
                </div>
              </div>
            </el-card>

            <el-card class="chart-card quick-card" shadow="never">
              <div class="quick-card__title">快捷操作</div>
              <div class="quick-grid">
                <button
                  v-for="action in quickActions"
                  :key="action.key"
                  type="button"
                  class="quick-action"
                  :style="{ '--action-color': action.color }"
                  :title="action.label"
                  @click="onQuickAction(action)"
                >
                  <el-icon class="quick-action__icon" :size="22">
                    <component :is="action.icon" />
                  </el-icon>
                  <span class="quick-action__label">{{ action.label }}</span>
                </button>
              </div>
            </el-card>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getStatsApi } from '@/api/dashboard'
import {
  Search,
  DataAnalysis,
  FolderOpened,
  Document,
  ChatDotRound,
  Download,
  Monitor,
  Setting
} from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)

const emptyStats = () => ({
  kb_count: 0,
  doc_count: 0,
  user_count: 0,
  group_count: 0,
  chunk_total: 0,
  avg_chunks_per_kb: 0,
  docs_by_status: {},
  docs_by_file_type: {},
  today_new_docs: 0,
  failed_doc_count: 0,
  failed_docs: [],
  question_count: 0,
  message_count: 0,
  session_count: 0,
  today_question_count: 0,
  avg_session_rounds: 0,
  max_session_rounds: 0,
  services: [],
  alerts: [],
  generated_at: ''
})

const stats = ref(emptyStats())
const statsReady = ref(false)
const now = ref(new Date())
const pageStartedAt = ref(Date.now())
let clockTimer = 0
let pollTimer = 0
const POLL_MS = 10000

const pad2 = (n) => String(n).padStart(2, '0')

const clockTime = computed(() => {
  const d = now.value
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
})

const clockDate = computed(() =>
  now.value.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short'
  })
)

const timeZoneText = computed(() => {
  const offsetMin = -now.value.getTimezoneOffset()
  const sign = offsetMin >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMin)
  return `UTC${sign}${pad2(Math.floor(abs / 60))}:${pad2(abs % 60)}`
})

const stayText = computed(() => {
  const totalSec = Math.max(0, Math.floor((now.value.getTime() - pageStartedAt.value) / 1000))
  const hours = Math.floor(totalSec / 3600)
  const mins = Math.floor((totalSec % 3600) / 60)
  const secs = totalSec % 60
  return `${pad2(hours)}:${pad2(mins)}:${pad2(secs)}`
})

/** 2 列 × 4 行；前 6 项按你指定，后 2 项补齐运维配置入口 */
const quickActions = [
  { key: 'hit', label: '命中率测试', path: '/hit-test', icon: Search, color: '#4A7AFF' },
  { key: 'retrieve', label: '检索效果校验', path: '/hit-test', icon: DataAnalysis, color: '#13C2C2' },
  { key: 'kb', label: '知识库管理', path: '/knowledge-bases', icon: FolderOpened, color: '#52C41A' },
  { key: 'docs', label: '知识文档库', path: '/documents', icon: Document, color: '#FA8C16' },
  { key: 'chat', label: '智能对话后台', path: '/chat', icon: ChatDotRound, color: '#722ED1' },
  { key: 'export', label: '导出问答报表', action: 'export-chat-report', icon: Download, color: '#EB2F96' },
  { key: 'models', label: '大模型管理', path: '/models', icon: Monitor, color: '#FAAD14' },
  { key: 'branding', label: '自定义设置', path: '/branding', icon: Setting, color: '#2F54EB' }
]

function onQuickAction(action) {
  if (action.action === 'export-chat-report') {
    exportChatReport()
    return
  }
  if (action.path) router.push(action.path)
}

function exportChatReport() {
  const s = stats.value
  const lines = [
    ['指标', '数值'],
    ['累计提问', s.question_count],
    ['今日提问', s.today_question_count],
    ['会话数', s.session_count],
    ['消息总数', s.message_count],
    ['平均轮次', s.avg_session_rounds],
    ['最长轮次', s.max_session_rounds],
    ['知识库数', s.kb_count],
    ['文档数', s.doc_count],
    ['切片总量', s.chunk_total],
    ['导出时间', new Date().toLocaleString('zh-CN')]
  ]
  const csv = lines
    .map((row) => row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `问答运营报表_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('问答报表已导出')
}

const STATUS_META = {
  completed: { label: '已完成', color: '#52C41A' },
  processing: { label: '处理中', color: '#4A7AFF' },
  pending: { label: '待处理', color: '#FAAD14' },
  failed: { label: '失败', color: '#F56C6C' },
  unknown: { label: '未知', color: '#8C8C8C' }
}

const TYPE_COLORS = ['#4A7AFF', '#52C41A', '#FA8C16', '#722ED1', '#13C2C2', '#EB2F96']

function toBars(map, metaFn) {
  const entries = Object.entries(map || {})
  const max = Math.max(...entries.map(([, v]) => Number(v) || 0), 1)
  return entries
    .map(([key, value], i) => {
      const meta = metaFn(key, i)
      const num = Number(value) || 0
      return {
        key,
        label: meta.label,
        color: meta.color,
        value: num,
        pct: Math.max(4, Math.round((num / max) * 100))
      }
    })
    .sort((a, b) => b.value - a.value)
}

const statusBars = computed(() =>
  toBars(stats.value.docs_by_status, (key) => STATUS_META[key] || STATUS_META.unknown)
)

const typeBars = computed(() =>
  toBars(stats.value.docs_by_file_type, (key, i) => ({
    label: String(key).toUpperCase(),
    color: TYPE_COLORS[i % TYPE_COLORS.length]
  }))
)

const statCards = computed(() => [
  {
    key: 'kb',
    label: '知识库',
    value: stats.value.kb_count,
    icon: 'KB',
    color: '#4A7AFF',
    desc: '知识资产空间'
  },
  {
    key: 'doc',
    label: '文档',
    value: stats.value.doc_count,
    icon: 'DOC',
    color: '#52C41A',
    desc: `失败 ${stats.value.failed_doc_count}`
  },
  {
    key: 'chunk',
    label: '切片总量',
    value: stats.value.chunk_total,
    icon: 'CHK',
    color: '#13C2C2',
    desc: 'chunks 表计数'
  },
  {
    key: 'q',
    label: '累计提问',
    value: stats.value.question_count,
    icon: 'ASK',
    color: '#FA8C16',
    desc: `今日 ${stats.value.today_question_count}`
  },
  {
    key: 'session',
    label: '会话数',
    value: stats.value.session_count,
    icon: 'SES',
    color: '#722ED1',
    desc: 'distinct session'
  },
  {
    key: 'user',
    label: '用户',
    value: stats.value.user_count,
    icon: 'USR',
    color: '#EB2F96',
    desc: `用户组 ${stats.value.group_count}`
  }
])

const chatMetrics = computed(() => [
  { label: '累计提问', value: stats.value.question_count, color: '#FA8C16' },
  { label: '今日提问', value: stats.value.today_question_count, color: '#4A7AFF' },
  { label: '会话数', value: stats.value.session_count, color: '#722ED1' },
  { label: '消息总数', value: stats.value.message_count, color: '#13C2C2' },
  { label: '平均轮次', value: stats.value.avg_session_rounds, color: '#52C41A' },
  { label: '最长轮次', value: stats.value.max_session_rounds, color: '#EB2F96' }
])

const chatBarMetrics = computed(() => {
  const items = chatMetrics.value
  const max = Math.max(...items.map((i) => Number(i.value) || 0), 1)
  return items.map((i) => ({
    ...i,
    pct: Math.max(8, Math.round((Number(i.value) || 0) / max * 100))
  }))
})

async function reload(silent = false) {
  if (!silent) loading.value = true
  try {
    stats.value = await getStatsApi()
    statsReady.value = true
  } catch (e) {
    console.error(e)
  } finally {
    if (!silent) loading.value = false
  }
}

onMounted(() => {
  pageStartedAt.value = Date.now()
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
  reload(false)
  pollTimer = window.setInterval(() => {
    reload(true)
  }, POLL_MS)
})

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
  if (pollTimer) window.clearInterval(pollTimer)
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  /* layout-body 上下 12+12 + header；.main 概览模式已去掉底 padding */
  height: 100%;
  max-height: 100%;
  overflow: hidden;
  color: var(--admin-text);
}

/* 覆盖全局 page-shell 自动高度，避免底部留白 */
.dashboard.dashboard--fill.page-shell {
  display: flex !important;
  height: 100% !important;
  max-height: 100% !important;
  overflow: hidden !important;
}

.dashboard :deep(.page-header),
.dashboard .page-header {
  flex-shrink: 0;
  margin-bottom: 10px !important;
  padding-bottom: 8px !important;
}

.dash-body {
  display: flex !important;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 0 2px 0 !important;
  gap: 12px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  color: var(--admin-text-muted);
  background: color-mix(in srgb, var(--admin-text) 8%, transparent);
  border: 1px solid var(--admin-border);
  border-radius: 999px;
  font-size: 13px;
}

.pulse {
  width: 8px;
  height: 8px;
  background: #52c41a;
  border-radius: 50%;
  box-shadow: 0 0 0 6px rgba(82, 196, 26, 0.12);
}

.header-badge.is-stale .pulse {
  background: #faad14;
  box-shadow: 0 0 0 6px rgba(250, 173, 20, 0.12);
}

.stat-grid {
  flex-shrink: 0;
  margin-bottom: 0 !important;
}

.chart-grid {
  flex: 1 1 0;
  min-height: 0;
  margin-bottom: 0 !important;
  align-items: stretch !important;
}

.dash-body :deep(.chart-grid.el-row) {
  height: 100%;
}

.dash-body :deep(.chart-col.el-col) {
  display: flex;
  height: 100%;
  min-height: 0;
}

.chart-col {
  display: flex;
  height: 100%;
  min-height: 0;
}

.stat-card,
.chart-card {
  height: 100%;
  color: var(--admin-text);
  margin-bottom: 0;
}

.chart-card--fill {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chart-card--fill :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 14px 16px;
}

.chart-card--center .card-title {
  justify-content: center;
  text-align: center;
  margin-bottom: 10px;
  flex-shrink: 0;
}

.chart-card--center .card-title h3 {
  margin-bottom: 0;
}

.chart-card--center .dist-block__title,
.chart-card--center .dist-meta,
.chart-card--center .dist-row__label,
.chart-card--center .dist-row__value,
.chart-card--center .empty-tip {
  text-align: center;
}

.chart-card--center .dist-meta {
  justify-content: center;
}

.stat-card :deep(.el-card__body),
.chart-card :deep(.el-card__body) {
  background: transparent;
  color: inherit;
}

.stat-card :deep(.el-card__body) {
  padding: 12px 14px;
}

.stat-main {
  display: flex;
  align-items: center;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  margin-right: 10px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  border-radius: 10px;
  color: var(--card-color, var(--el-color-primary));
  background: color-mix(in srgb, var(--card-color, var(--el-color-primary)) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--card-color, var(--el-color-primary)) 35%, transparent);
}

.stat-info {
  flex: 1;
  min-width: 0;
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--admin-text);
  text-align: center;
}

.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--admin-text-muted);
  text-align: center;
}

.stat-footer {
  margin-top: 10px;
  padding-top: 8px;
  font-size: 11px;
  color: var(--admin-text-dim);
  border-top: 1px solid var(--glass-divider);
}

.card-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.bar-chart {
  display: flex;
  align-items: stretch;
  justify-content: space-around;
  gap: 6px;
  flex: 1;
  min-height: 0;
  padding: 4px 4px 0;
}

.bar-item {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 0;
  height: 100%;
  cursor: pointer;
}

.bar-value {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--admin-text);
  transition: color 0.2s ease;
}

.bar-track {
  display: flex;
  align-items: flex-end;
  flex: 1;
  width: 42%;
  min-width: 18px;
  max-width: 36px;
  min-height: 64px;
  padding: 3px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid color-mix(in srgb, var(--bar-color) 22%, transparent);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.bar-fill {
  width: 100%;
  min-height: 10px;
  border-radius: 999px;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--bar-color) 88%, #fff 12%) 0%,
    var(--bar-color) 100%
  );
  box-shadow: 0 0 12px color-mix(in srgb, var(--bar-color) 35%, transparent);
  transition: height 0.35s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

.bar-item:hover .bar-track {
  border-color: color-mix(in srgb, var(--bar-color) 85%, #fff 15%);
  background: color-mix(in srgb, var(--bar-color) 12%, rgba(255, 255, 255, 0.04));
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--bar-color) 55%, transparent),
    0 0 14px color-mix(in srgb, var(--bar-color) 55%, transparent),
    0 0 28px color-mix(in srgb, var(--bar-color) 28%, transparent);
}

.bar-item:hover .bar-fill {
  filter: brightness(1.08);
  box-shadow: 0 0 16px color-mix(in srgb, var(--bar-color) 55%, transparent);
}

.bar-item:hover .bar-value {
  color: var(--bar-color);
}

.bar-label {
  flex-shrink: 0;
  font-size: 11px;
  line-height: 1.2;
  text-align: center;
  color: var(--admin-text-muted);
  white-space: nowrap;
  transition: color 0.2s ease;
}

.bar-item:hover .bar-label {
  color: color-mix(in srgb, var(--bar-color) 70%, var(--admin-text-muted));
}

.dist-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
  align-content: center;
}

.dist-block__title {
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--admin-text-muted);
}

.dist-row {
  display: grid;
  grid-template-columns: 56px 1fr 32px;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.dist-row__label {
  font-size: 12px;
  color: var(--admin-text-muted);
}

.dist-row__track {
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.dist-row__fill {
  height: 100%;
  border-radius: 999px;
  min-width: 4px;
}

.dist-row__value {
  text-align: right;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--admin-text);
}

.dist-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--glass-divider);
  font-size: 12px;
  color: var(--admin-text-muted);
  flex-shrink: 0;
}

.dist-meta strong {
  color: var(--admin-text);
  font-variant-numeric: tabular-nums;
}

.empty-tip {
  margin: 0;
  font-size: 13px;
  color: var(--admin-text-dim);
}

.main-stack,
.side-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
}

/* 右侧：时间固定内容高度，快捷操作吃满剩余空间 */
.side-stack {
  display: grid;
  grid-template-rows: auto minmax(200px, 1fr);
  align-content: stretch;
}

.chat-card {
  flex: 1.35;
  min-height: 0;
}

.asset-card {
  flex: 1;
  min-height: 0;
}

.time-card.chart-card {
  flex: none;
  height: auto !important;
  align-self: stretch;
}

.time-card :deep(.el-card__body) {
  display: block;
  height: auto !important;
  flex: none !important;
  min-height: 0;
  padding: 14px 16px 12px;
}

.quick-card.chart-card {
  flex: none;
  height: 100% !important;
  min-height: 200px;
  overflow: hidden;
}

.quick-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 14px 16px;
}

.time-card__label {
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(180, 190, 210, 0.55);
}

.time-card__clock {
  margin-top: 8px;
  text-align: center;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
  color: var(--el-color-primary);
  line-height: 1.1;
}

.time-card__date {
  margin-top: 6px;
  text-align: center;
  font-size: 13px;
  color: rgba(230, 235, 245, 0.92);
}

.time-card__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(160, 170, 190, 0.28);
}

.time-meta-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(120, 160, 255, 0.12);
  text-align: center;
}

.time-meta-box__label {
  font-size: 11px;
  color: rgba(180, 190, 210, 0.55);
  text-align: center;
}

.time-meta-box__value {
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.quick-card__title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  flex-shrink: 0;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(4, minmax(0, 1fr));
  gap: 14px;
  flex: 1;
  min-height: 0;
}

.quick-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 0;
  height: 100%;
  padding: 12px 10px;
  border-radius: 18px;
  border: 1px solid var(--glass-border, rgba(120, 160, 255, 0.14));
  background-color: rgba(10, 18, 36, 0.15);
  background-image: var(--admin-card-tint, none);
  background-repeat: no-repeat;
  color: inherit;
  cursor: pointer;
  transform: translateY(0) scale(1);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    filter 0.2s ease,
    transform 0.15s ease;
}

.quick-action:hover {
  border-color: color-mix(in srgb, var(--el-color-primary) 45%, var(--glass-border, rgba(120, 160, 255, 0.14)));
  box-shadow: var(--glass-shadow, 0 0 12px color-mix(in srgb, var(--el-color-primary) 18%, transparent));
  filter: brightness(1.06);
}

.quick-action:active {
  transform: translateY(1px) scale(0.96);
  filter: brightness(0.92);
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.28);
  border-color: color-mix(in srgb, var(--el-color-primary) 55%, var(--glass-border, rgba(120, 160, 255, 0.14)));
}

.quick-action__icon {
  color: var(--action-color, var(--el-color-primary));
}

.quick-action__label {
  font-size: 13px;
  font-weight: 400;
  line-height: 1.25;
  text-align: center;
  color: rgba(230, 235, 245, 0.95);
  word-break: break-word;
}

@media (max-width: 992px) {
  .dashboard {
    height: auto;
    max-height: none;
    overflow: visible;
  }

  .dash-body {
    overflow: visible;
  }

  .chart-grid {
    flex: none;
  }

  .chart-col,
  .main-stack,
  .side-stack,
  .chat-card,
  .asset-card,
  .quick-card {
    height: auto;
    flex: none;
  }

  .bar-chart {
    min-height: 180px;
  }

  .dist-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .header-badge {
    align-self: flex-start;
  }
}
</style>
