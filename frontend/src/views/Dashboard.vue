<template>
  <div class="dashboard page-shell">
    <div class="page-header">
      <h2>系统概览</h2>
      <div class="header-badge">
        <span class="pulse"></span>
        数据实时同步
      </div>
    </div>

    <div class="page-body">
    <el-row :gutter="20" class="chart-grid">
      <el-col :xs="24" :lg="16" class="trend-col">
        <el-card class="chart-card trend-card" shadow="never">
          <div class="card-title">
            <div>
              <h3>能力趋势</h3>
              <p>以当前统计数据生成的运营趋势视图</p>
            </div>
          </div>
          <div class="trend-chart-wrap">
            <svg
              class="trend-chart"
              viewBox="0 0 640 280"
              preserveAspectRatio="xMidYMid meet"
              role="img"
              aria-label="系统能力趋势"
            >
              <defs>
                <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stop-color="#4A7AFF" stop-opacity="0.28" />
                  <stop offset="100%" stop-color="#4A7AFF" stop-opacity="0.02" />
                </linearGradient>
              </defs>
              <g class="grid-lines">
                <line
                  v-for="y in trendGridYs"
                  :key="y"
                  :x1="trendPlot.left"
                  :x2="trendPlot.right"
                  :y1="y"
                  :y2="y"
                />
              </g>
              <path :d="trendAreaPath" fill="url(#trendFill)" />
              <path
                :d="trendLinePath"
                fill="none"
                stroke="#4A7AFF"
                stroke-width="4"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <g
                v-for="point in trendPoints"
                :key="point.label"
                class="trend-point"
                @mouseenter="hoverTrendPoint = point"
                @mouseleave="hoverTrendPoint = null"
              >
                <circle
                  class="trend-point__hit"
                  :cx="point.x"
                  :cy="point.y"
                  r="16"
                  fill="transparent"
                />
                <circle
                  class="trend-point__dot"
                  :cx="point.x"
                  :cy="point.y"
                  r="5"
                  fill="#ffffff"
                  stroke="#4A7AFF"
                  stroke-width="3"
                />
              </g>
              <text
                v-for="point in trendPoints"
                :key="`${point.label}-text`"
                :x="point.x"
                :y="trendPlot.labelY"
              >{{ point.label }}</text>
            </svg>
            <div
              v-if="hoverTrendPoint"
              class="trend-tooltip"
              :style="trendTooltipStyle"
            >
              <strong>{{ hoverTrendPoint.label }}</strong>
              <span>{{ hoverTrendPoint.value }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <div class="side-stack">
          <el-card class="chart-card time-card" shadow="never">
            <div class="time-card__label">系统时间</div>
            <div class="time-card__clock">{{ clockTime }}</div>
            <div class="time-card__date">{{ clockDate }}</div>
            <div class="time-card__meta">
              <div class="time-meta-box">
                <span class="time-meta-box__label">运行时长</span>
                <strong class="time-meta-box__value">{{ uptimeText }}</strong>
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
                :key="action.path"
                type="button"
                class="quick-action"
                @click="goQuick(action.path)"
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

    <el-row :gutter="20" class="stat-grid">
      <el-col v-for="card in statCards" :key="card.key" :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card" shadow="never" :style="{ '--card-color': card.color }">
          <div class="stat-main">
            <div class="stat-icon" :style="{ '--card-color': card.color }">{{ card.icon }}</div>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
          <div class="stat-footer">
            <span>{{ card.desc }}</span>
            <span class="stat-chip" :style="{ color: card.color }">{{ card.rate }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStatsApi } from '@/api/dashboard'
import { Search, Refresh, FolderOpened, ChatDotRound } from '@element-plus/icons-vue'

const router = useRouter()

const stats = ref({
  kb_count: 0,
  doc_count: 0,
  user_count: 0,
  group_count: 0
})

const now = ref(new Date())
const sessionStartedAt = ref(Date.now())
let clockTimer = 0

const pad2 = (n) => String(n).padStart(2, '0')

const clockTime = computed(() => {
  const d = now.value
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
})

const clockDate = computed(() =>
  now.value.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
)

const timeZoneText = computed(() => {
  const offsetMin = -now.value.getTimezoneOffset()
  const sign = offsetMin >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMin)
  return `UTC${sign}${pad2(Math.floor(abs / 60))}:${pad2(abs % 60)}`
})

const uptimeText = computed(() => {
  const totalSec = Math.max(0, Math.floor((now.value.getTime() - sessionStartedAt.value) / 1000))
  const days = Math.floor(totalSec / 86400)
  const hours = Math.floor((totalSec % 86400) / 3600)
  const mins = Math.floor((totalSec % 3600) / 60)
  const secs = totalSec % 60
  return `${days}d ${pad2(hours)}:${pad2(mins)}:${pad2(secs)}`
})

const quickActions = [
  { label: '命中测试', path: '/hit-test', icon: Search },
  { label: '同步数据', path: '/documents', icon: Refresh },
  { label: '知识库', path: '/knowledge-bases', icon: FolderOpened },
  { label: '智能对话', path: '/chat', icon: ChatDotRound }
]

function goQuick(path) {
  router.push(path)
}

const statCards = computed(() => {
  const items = [
    {
      key: 'kb_count',
      label: '知识库数量',
      shortLabel: '知识库',
      value: stats.value.kb_count,
      icon: 'KB',
      color: '#4A7AFF',
      gradient: 'linear-gradient(180deg, #6B93FF 0%, #4A7AFF 100%)',
      desc: '知识资产空间',
      rate: '+12%'
    },
    {
      key: 'doc_count',
      label: '文档数量',
      shortLabel: '文档',
      value: stats.value.doc_count,
      icon: 'DOC',
      color: '#52C41A',
      gradient: 'linear-gradient(180deg, #7ED957 0%, #52C41A 100%)',
      desc: '已接入文档',
      rate: '+18%'
    },
    {
      key: 'group_count',
      label: '用户组数量',
      shortLabel: '用户组',
      value: stats.value.group_count,
      icon: 'GRP',
      color: '#722ED1',
      gradient: 'linear-gradient(180deg, #9254DE 0%, #722ED1 100%)',
      desc: '组织权限分组',
      rate: '+6%'
    },
    {
      key: 'user_count',
      label: '用户数量',
      shortLabel: '用户',
      value: stats.value.user_count,
      icon: 'USR',
      color: '#FA8C16',
      gradient: 'linear-gradient(180deg, #FFB45C 0%, #FA8C16 100%)',
      desc: '平台成员规模',
      rate: '+8%'
    }
  ]
  const max = Math.max(...items.map((item) => item.value), 1)
  return items.map((item) => ({
    ...item,
    percent: Math.max(8, Math.round((item.value / max) * 100))
  }))
})

const totalCount = computed(() => statCards.value.reduce((sum, item) => sum + item.value, 0))

const hoverTrendPoint = ref(null)

/** 绘图区留白：左右 48、上 28、下标签区 44 */
const trendPlot = {
  left: 48,
  right: 592,
  top: 28,
  bottom: 220,
  labelY: 258,
  width: 544,
  height: 192
}

const trendGridYs = computed(() => {
  const { top, height } = trendPlot
  return [0, 0.25, 0.5, 0.75, 1].map((t) => top + height * t)
})

const trendPoints = computed(() => {
  const values = [
    stats.value.kb_count,
    stats.value.doc_count,
    stats.value.group_count,
    stats.value.user_count,
    totalCount.value
  ]
  const labels = ['知识库', '文档', '用户组', '用户', '总览']
  const max = Math.max(...values, 1)
  const n = values.length
  const { left, width, top, height, bottom } = trendPlot
  return values.map((value, index) => {
    const x = n === 1 ? left + width / 2 : left + (index / (n - 1)) * width
    const ratio = value / max
    const y = bottom - Math.max(8, ratio * height)
    return {
      label: labels[index],
      value,
      x,
      y,
      // 相对容器百分比，供 tooltip 定位
      leftPct: (x / 640) * 100,
      topPct: (y / 280) * 100
    }
  })
})

const trendTooltipStyle = computed(() => {
  const p = hoverTrendPoint.value
  if (!p) return {}
  return {
    left: `${p.leftPct}%`,
    top: `${p.topPct}%`
  }
})

/** Catmull-Rom → 三次贝塞尔，折线改平滑曲线 */
function buildSmoothPath(points) {
  if (!points.length) return ''
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`
  if (points.length === 2) {
    return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`
  }
  let d = `M ${points[0].x} ${points[0].y}`
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i]
    const p1 = points[i]
    const p2 = points[i + 1]
    const p3 = points[i + 2] || p2
    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = p1.y + (p2.y - p0.y) / 6
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`
  }
  return d
}

const trendLinePath = computed(() => buildSmoothPath(trendPoints.value))

const trendAreaPath = computed(() => {
  const points = trendPoints.value
  if (!points.length) return ''
  const baseY = trendPlot.bottom
  return `${trendLinePath.value} L ${points[points.length - 1].x} ${baseY} L ${points[0].x} ${baseY} Z`
})

onMounted(async () => {
  sessionStartedAt.value = Date.now()
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
  try {
    const data = await getStatsApi()
    stats.value = {
      kb_count: data.kb_count ?? 0,
      doc_count: data.doc_count ?? 0,
      user_count: data.user_count ?? 0,
      group_count: data.group_count ?? 0
    }
  } catch (error) {
    console.error(error)
  }
})

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})
</script>

<style scoped>
.dashboard {
  color: var(--admin-text);
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

.stat-grid,
.chart-grid {
  margin-bottom: 20px;
}

.chart-grid {
  align-items: stretch;
}

.trend-col {
  display: flex;
}

.trend-col > .trend-card {
  width: 100%;
}

.stat-card,
.chart-card {
  height: 100%;
  color: var(--admin-text);
}

.stat-card :deep(.el-card__body),
.chart-card :deep(.el-card__body) {
  background: transparent;
  color: inherit;
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
  width: 52px;
  height: 52px;
  margin-right: 16px;
  font-size: 12px;
  font-weight: 700;
  color: var(--card-color);
  background: color-mix(in srgb, var(--card-color) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--card-color) 28%, transparent);
  border-radius: var(--admin-radius-sm);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  color: var(--admin-text);
}

.stat-label {
  font-size: 14px;
  color: var(--admin-text-muted);
  margin-top: 8px;
}

.stat-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 18px;
  padding-top: 14px;
  font-size: 12px;
  color: var(--admin-text-dim);
  border-top: 1px solid var(--glass-divider);
}

.stat-chip {
  font-weight: 700;
}

.card-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.card-title h3 {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 600;
  color: var(--admin-text);
}

.card-title p {
  margin: 0;
  font-size: 13px;
  color: var(--admin-text-muted);
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 280px;
  padding: 16px 8px 0;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--admin-border);
  border-radius: var(--admin-radius);
}

.bar-item {
  display: flex;
  align-items: center;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  height: 100%;
}

.bar-track {
  display: flex;
  align-items: flex-end;
  width: 42px;
  height: 190px;
  padding: 4px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 999px;
  transition: box-shadow 0.22s ease;
}

.bar-fill {
  width: 100%;
  min-height: 12px;
  border-radius: 999px;
  transition: filter 0.22s ease;
}

.bar-item:hover .bar-track {
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--card-color) 65%, transparent),
    0 0 18px color-mix(in srgb, var(--card-color) 45%, transparent);
}

.bar-item:hover .bar-fill {
  filter: drop-shadow(0 0 10px color-mix(in srgb, var(--card-color) 70%, transparent));
}

.bar-value {
  font-weight: 700;
  color: var(--admin-text);
}

.bar-label {
  font-size: 12px;
  color: var(--admin-text-muted);
}

.side-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  min-height: 0;
}

.time-card,
.quick-card {
  overflow: visible;
}

.time-card :deep(.el-card__body),
.quick-card :deep(.el-card__body) {
  padding: 18px 18px 16px;
  overflow: visible;
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
  margin-top: 10px;
  text-align: center;
  font-size: 36px;
  font-weight: 700;
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
  color: var(--el-color-primary);
  text-shadow: 0 0 18px color-mix(in srgb, var(--el-color-primary) 45%, transparent);
  line-height: 1.1;
}

.time-card__date {
  margin-top: 8px;
  text-align: center;
  font-size: 15px;
  color: rgba(230, 235, 245, 0.92);
}

.time-card__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(160, 170, 190, 0.28);
}

.time-meta-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(120, 160, 255, 0.12);
}

.time-meta-box__label {
  font-size: 12px;
  color: rgba(180, 190, 210, 0.55);
}

.time-meta-box__value {
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: rgba(235, 240, 250, 0.92);
}

.quick-card {
  flex: 1 1 auto;
  overflow: visible;
}

.quick-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 260px;
  overflow: visible;
}

.quick-card__title {
  margin-bottom: 14px;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.quick-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex: 1;
  min-height: 220px;
}

.quick-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 100px;
  height: 100%;
  padding: 16px 10px;
  border-radius: 12px;
  border: 1px solid rgba(120, 160, 255, 0.14);
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.quick-action:hover {
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
  border-color: color-mix(in srgb, var(--el-color-primary) 40%, transparent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--el-color-primary) 22%, transparent);
}

.quick-action__icon {
  color: var(--el-color-primary);
}

.quick-action__label {
  font-size: 13px;
  color: rgba(230, 235, 245, 0.9);
}

.trend-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.trend-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: visible;
  padding: 18px 20px 16px;
}

.trend-chart-wrap {
  position: relative;
  flex: 1;
  min-height: 280px;
  margin-top: 4px;
  padding: 4px 8px 0;
}

.trend-chart {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 280px;
  border-radius: 12px;
}

.trend-point {
  cursor: pointer;
}

.trend-point__dot {
  transition: r 0.15s ease, filter 0.15s ease;
}

.trend-point:hover .trend-point__dot {
  filter: drop-shadow(0 0 8px #4A7AFF);
}

.trend-tooltip {
  position: absolute;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 72px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(120, 160, 255, 0.28);
  background: rgba(12, 18, 32, 0.92);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
  pointer-events: none;
  transform: translate(-50%, calc(-100% - 12px));
  white-space: nowrap;
}

.trend-tooltip strong {
  font-size: 12px;
  font-weight: 600;
  color: rgba(220, 230, 245, 0.9);
}

.trend-tooltip span {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--el-color-primary);
}

.grid-lines line {
  stroke: var(--glass-divider);
  stroke-dasharray: 4 6;
}

.trend-chart text {
  font-size: 13px;
  text-anchor: middle;
  fill: var(--admin-text-muted);
}

.dashboard :deep(.el-tag) {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--admin-border);
  color: var(--admin-text-muted);
}

@media (max-width: 768px) {
  .header-badge {
    align-self: flex-start;
  }
}
</style>
