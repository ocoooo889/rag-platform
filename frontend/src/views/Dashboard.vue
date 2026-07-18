<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <div>
        <p class="eyebrow">Dashboard</p>
        <h2>系统概览</h2>
        <span>集中查看知识资产、用户组织与系统运行概况</span>
      </div>
      <div class="header-badge">
        <span class="pulse"></span>
        数据实时同步
      </div>
    </div>

    <el-row :gutter="20" class="stat-grid">
      <el-col v-for="card in statCards" :key="card.key" :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card" shadow="never">
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

    <el-row :gutter="20" class="chart-grid">
      <el-col :xs="24" :lg="14">
        <el-card class="chart-card" shadow="never">
          <div class="card-title">
            <div>
              <h3>资源分布</h3>
              <p>基于当前系统统计值生成</p>
            </div>
            <el-tag type="primary" effect="plain">总量 {{ totalCount }}</el-tag>
          </div>
          <div class="bar-chart">
            <div v-for="item in statCards" :key="item.key" class="bar-item">
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{ height: `${item.percent}%`, background: item.gradient }"
                ></div>
              </div>
              <span class="bar-value">{{ item.value }}</span>
              <span class="bar-label">{{ item.shortLabel }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card class="chart-card" shadow="never">
          <div class="card-title">
            <div>
              <h3>资产占比</h3>
              <p>知识库与文档资产构成</p>
            </div>
          </div>
          <div class="donut-section">
            <div class="donut" :style="{ background: donutGradient }">
              <div class="donut-center">
                <strong>{{ assetTotal }}</strong>
                <span>资产总量</span>
              </div>
            </div>
            <div class="legend-list">
              <div v-for="item in assetCards" :key="item.key" class="legend-item">
                <span class="legend-dot" :style="{ background: item.color }"></span>
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-grid">
      <el-col :xs="24" :lg="16">
        <el-card class="chart-card" shadow="never">
          <div class="card-title">
            <div>
              <h3>能力趋势</h3>
              <p>以当前统计数据生成的运营趋势视图</p>
            </div>
          </div>
          <svg class="trend-chart" viewBox="0 0 640 220" role="img" aria-label="系统能力趋势">
            <defs>
              <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#4A7AFF" stop-opacity="0.28" />
                <stop offset="100%" stop-color="#4A7AFF" stop-opacity="0.02" />
              </linearGradient>
            </defs>
            <g class="grid-lines">
              <line v-for="y in [40, 80, 120, 160, 200]" :key="y" x1="40" x2="610" :y1="y" :y2="y" />
            </g>
            <path :d="trendAreaPath" fill="url(#trendFill)" />
            <path :d="trendLinePath" fill="none" stroke="#4A7AFF" stroke-width="4" stroke-linecap="round" />
            <circle
              v-for="point in trendPoints"
              :key="point.label"
              :cx="point.x"
              :cy="point.y"
              r="5"
              fill="#ffffff"
              stroke="#4A7AFF"
              stroke-width="3"
            />
            <text v-for="point in trendPoints" :key="`${point.label}-text`" :x="point.x" y="214">{{ point.label }}</text>
          </svg>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="chart-card status-panel" shadow="never">
          <div class="card-title">
            <div>
              <h3>系统状态</h3>
              <p>核心模块健康度</p>
            </div>
          </div>
          <div class="status-list">
            <div v-for="item in statusItems" :key="item.label" class="status-item">
              <div>
                <strong>{{ item.label }}</strong>
                <span>{{ item.desc }}</span>
              </div>
              <el-progress :percentage="item.percent" :color="item.color" :stroke-width="8" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { getStatsApi } from '@/api/dashboard'

const stats = ref({
  kb_count: 0,
  doc_count: 0,
  user_count: 0,
  group_count: 0
})

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
      key: 'user_count',
      label: '用户数量',
      shortLabel: '用户',
      value: stats.value.user_count,
      icon: 'USR',
      color: '#FA8C16',
      gradient: 'linear-gradient(180deg, #FFB45C 0%, #FA8C16 100%)',
      desc: '平台成员规模',
      rate: '+8%'
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
    }
  ]
  const max = Math.max(...items.map((item) => item.value), 1)
  return items.map((item) => ({
    ...item,
    percent: Math.max(8, Math.round((item.value / max) * 100))
  }))
})

const assetCards = computed(() => statCards.value.slice(0, 2))
const assetTotal = computed(() => assetCards.value.reduce((sum, item) => sum + item.value, 0))
const totalCount = computed(() => statCards.value.reduce((sum, item) => sum + item.value, 0))

const donutGradient = computed(() => {
  if (!assetTotal.value) {
    return 'conic-gradient(#e8eef7 0deg 360deg)'
  }
  const kbDeg = Math.round((stats.value.kb_count / assetTotal.value) * 360)
  return `conic-gradient(#4A7AFF 0deg ${kbDeg}deg, #52C41A ${kbDeg}deg 360deg)`
})

const trendPoints = computed(() => {
  const values = [
    stats.value.kb_count,
    stats.value.doc_count,
    stats.value.user_count,
    stats.value.group_count,
    totalCount.value
  ]
  const labels = ['知识库', '文档', '用户', '用户组', '总览']
  const max = Math.max(...values, 1)
  return values.map((value, index) => ({
    label: labels[index],
    x: 60 + index * 135,
    y: 190 - Math.max(12, (value / max) * 145)
  }))
})

const trendLinePath = computed(() => {
  return trendPoints.value.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
})

const trendAreaPath = computed(() => {
  const points = trendPoints.value
  if (!points.length) return ''
  return `${trendLinePath.value} L ${points[points.length - 1].x} 200 L ${points[0].x} 200 Z`
})

const statusItems = computed(() => [
  {
    label: '知识库服务',
    desc: `${stats.value.kb_count} 个知识库可用`,
    percent: stats.value.kb_count ? 96 : 72,
    color: '#4A7AFF'
  },
  {
    label: '文档索引',
    desc: `${stats.value.doc_count} 份文档纳管`,
    percent: stats.value.doc_count ? 92 : 68,
    color: '#52C41A'
  },
  {
    label: '权限体系',
    desc: `${stats.value.user_count} 用户 / ${stats.value.group_count} 组`,
    percent: stats.value.user_count ? 88 : 64,
    color: '#FA8C16'
  }
])

onMounted(async () => {
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
</script>

<style scoped>
.dashboard {
  padding: 4px 0 8px;
}

.dashboard-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--color-primary);
  text-transform: uppercase;
}

.dashboard-header h2 {
  margin: 0 0 8px;
  font-size: 26px;
  color: var(--text-color-primary);
}

.dashboard-header span {
  color: var(--text-color-secondary);
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border: 1px solid var(--border-color-primary);
  border-radius: 999px;
}

.pulse {
  width: 8px;
  height: 8px;
  background: var(--color-success);
  border-radius: 50%;
  box-shadow: 0 0 0 6px rgba(82, 196, 26, 0.12);
}

.stat-grid,
.chart-grid {
  margin-bottom: 20px;
}

.stat-card {
  height: 100%;
  border: 1px solid var(--border-color-light);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-card-hover);
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
  width: 58px;
  height: 58px;
  margin-right: 16px;
  font-size: 13px;
  font-weight: 800;
  color: var(--card-color);
  background: color-mix(in srgb, var(--card-color) 13%, #ffffff);
  border-radius: 16px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  line-height: 1;
  color: var(--text-color-primary);
}

.stat-label {
  font-size: 14px;
  color: var(--text-color-secondary);
  margin-top: 8px;
}

.stat-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 18px;
  padding-top: 14px;
  font-size: 12px;
  color: var(--text-color-secondary);
  border-top: 1px solid var(--border-color-light);
}

.stat-chip {
  font-weight: 700;
}

.chart-card {
  height: 100%;
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
  font-size: 18px;
  color: var(--text-color-primary);
}

.card-title p {
  margin: 0;
  font-size: 13px;
  color: var(--text-color-secondary);
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 280px;
  padding: 16px 8px 0;
  background: linear-gradient(180deg, #fbfdff 0%, #ffffff 100%);
  border-radius: 12px;
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
  background: #eef4ff;
  border-radius: 999px;
}

.bar-fill {
  width: 100%;
  min-height: 12px;
  border-radius: 999px;
  box-shadow: 0 8px 18px rgba(74, 122, 255, 0.18);
}

.bar-value {
  font-weight: 800;
  color: var(--text-color-primary);
}

.bar-label {
  font-size: 12px;
  color: var(--text-color-secondary);
}

.donut-section {
  display: flex;
  align-items: center;
  gap: 24px;
  min-height: 280px;
}

.donut {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 170px;
  height: 170px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(74, 122, 255, 0.08);
}

.donut-center {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  width: 108px;
  height: 108px;
  background: #ffffff;
  border-radius: 50%;
  box-shadow: var(--shadow-card);
}

.donut-center strong {
  font-size: 26px;
  color: var(--text-color-primary);
}

.donut-center span,
.legend-item span {
  color: var(--text-color-secondary);
}

.legend-list {
  flex: 1;
}

.legend-item {
  display: grid;
  align-items: center;
  grid-template-columns: 12px 1fr auto;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color-light);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.trend-chart {
  width: 100%;
  height: 260px;
}

.grid-lines line {
  stroke: #edf2f7;
  stroke-dasharray: 4 6;
}

.trend-chart text {
  font-size: 13px;
  text-anchor: middle;
  fill: #909399;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.status-item {
  padding: 16px;
  background: #f8fbff;
  border: 1px solid var(--border-color-light);
  border-radius: 12px;
}

.status-item strong,
.status-item span {
  display: block;
}

.status-item strong {
  margin-bottom: 5px;
  color: var(--text-color-primary);
}

.status-item span {
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .dashboard-header,
  .donut-section {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-badge {
    align-self: flex-start;
  }
}
</style>
