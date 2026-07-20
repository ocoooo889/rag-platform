<template>
  <div class="page-shell eval-page" v-loading="loading">
    <div class="page-header">
      <h2>评测任务</h2>
      <el-button type="primary" @click="openCreate">新建任务</el-button>
    </div>

    <div class="page-body">
      <div class="filter-bar">
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索任务名称"
          style="width: 200px"
          @change="onFilterChange"
        />
        <el-select
          v-model="statusFilter"
          clearable
          placeholder="任务状态"
          style="width: 160px"
          @change="onFilterChange"
        >
          <el-option label="等待中" value="pending" />
          <el-option label="运行中" value="running" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-button @click="loadTasks">刷新</el-button>
      </div>

      <el-table :data="tasks" stripe class="app-table table-cols-auto eval-task-table">
        <el-table-column prop="name" label="任务名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="知识库 / 模型" min-width="160">
          <template #default="{ row }">
            <div class="params-cell">
              <span>{{ row.params?.kb_name || row.params?.kb_id || '—' }}</span>
              <span class="muted">{{ row.params?.embedding_model || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="切分" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.params">
              {{ row.params.chunk_size }}/{{ row.params.chunk_overlap }}
            </span>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="样本" width="88" align="center">
          <template #default="{ row }">
            <el-button text type="primary" @click="openSamples(row)">
              {{ Number(row.sample_count) || 0 }} 条
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150" align="center">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'running' || (row.progress != null && row.progress > 0)"
              :percentage="Math.min(100, Number(row.progress) || 0)"
              :stroke-width="10"
              :status="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'exception' : undefined"
            />
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="220">
          <template #default="{ row }">
            <div class="ops-cell">
              <el-button
                link
                type="primary"
                :disabled="row.status === 'running'"
                :loading="runningId === row.id"
                @click="onRun(row)"
              >
                运行
              </el-button>
              <el-button link type="primary" @click="openResults(row)">结果</el-button>
              <el-button
                link
                :type="compareIds.includes(row.id) ? 'warning' : 'primary'"
                @click="toggleCompare(row)"
              >
                {{ compareIds.includes(row.id) ? '取消对比' : '对比' }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, prev, pager, next"
          :total="total"
          @current-change="loadTasks"
        />
      </div>

      <!-- 多任务对比 -->
      <div v-if="compareIds.length" class="compare-panel panel">
        <div class="panel-head">
          <div class="panel-head__text">
            <div class="panel-title">多任务指标对比</div>
            <p class="panel-sub">已选 {{ compareIds.length }} 个任务 · 指标范围 0～1，越高越好</p>
          </div>
          <el-button type="primary" :loading="compareLoading" @click="runCompare">
            生成对比
          </el-button>
        </div>

        <div v-if="compareInsight" class="insight-banner">
          <div class="insight-banner__title">{{ compareInsight.title }}</div>
          <p class="insight-banner__detail">{{ compareInsight.detail }}</p>
        </div>

        <div v-if="compareTable.length" class="compare-body">
          <div ref="lineChartRef" class="chart chart--compare" />
          <el-table :data="compareTable" size="small" class="compare-table table-cols-auto" stripe>
            <el-table-column label="指标" min-width="110">
              <template #default="{ row }">
                <span class="metric-cell">
                  <span class="metric-cell__cn">{{ metricCn(row.metric) }}</span>
                  <span class="metric-cell__en">{{ row.metric }}</span>
                </span>
              </template>
            </el-table-column>
            <el-table-column
              v-for="col in compareTaskCols"
              :key="col"
              :prop="col"
              :label="col"
              min-width="100"
              align="center"
            />
          </el-table>
        </div>
        <div v-else class="compare-empty muted">点击右上角「生成对比」查看图表与数值</div>

        <el-collapse v-model="metricGuideOpen" class="metric-collapse">
          <el-collapse-item title="指标说明（点击展开）" name="guide">
            <div class="metric-list">
              <div v-for="item in METRIC_GUIDE" :key="item.key" class="metric-list__row">
                <div class="metric-list__label">
                  <span class="metric-list__cn">{{ item.label }}</span>
                  <code>{{ item.key }}</code>
                </div>
                <p class="metric-list__desc">{{ item.desc }}</p>
                <p class="metric-list__tip">{{ item.tip }}</p>
              </div>
            </div>
            <p class="metric-foot muted">
              计算口径：样本「期望答案」与检索/回答文本的词重叠估算，便于任务间相对对比。
            </p>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>

    <!-- 新建任务 -->
    <el-dialog
      v-model="createVisible"
      title="新建评测任务"
      width="640px"
      destroy-on-close
      @closed="onCreateClosed"
    >
      <el-form label-width="110px" :disabled="creating">
        <el-form-item label="任务名称" required>
          <el-input v-model="createForm.name" maxlength="80" show-word-limit placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="知识库" required>
          <el-select
            v-model="createForm.kb_id"
            filterable
            placeholder="选择评测知识库"
            style="width: 100%"
            :loading="kbLoading"
            @change="onKbChange"
          >
            <el-option
              v-for="kb in kbList"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="向量模型">
          <el-select
            v-model="createForm.embedding_model"
            filterable
            style="width: 100%"
            :loading="modelsLoading"
            placeholder="从运行配置接口加载"
          >
            <el-option v-for="m in embeddingModels" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="文本块大小">
          <el-input-number
            v-model="createForm.chunk_size"
            :min="chunkSizeMin"
            :max="chunkSizeMax"
            :step="50"
          />
        </el-form-item>
        <el-form-item label="切片重叠">
          <el-input-number
            v-model="createForm.chunk_overlap"
            :min="0"
            :max="Math.max(0, createForm.chunk_size - 1)"
            :step="10"
          />
        </el-form-item>
        <el-form-item label="分块方式">
          <el-select
            v-model="createForm.chunk_mode"
            style="width: 100%"
            :loading="splitLoading"
            placeholder="从 split-strategies 加载"
            @change="onChunkModeChange"
          >
            <el-option
              v-for="opt in splitItems"
              :key="opt.value"
              :label="opt.is_default ? `${opt.label}（默认）` : opt.label"
              :value="opt.value"
            />
          </el-select>
          <p v-if="splitError" class="hint">{{ splitError }}</p>
        </el-form-item>
        <el-form-item label="分割符号">
          <el-input v-model="createForm.separators" placeholder="多个用 | 分隔" />
        </el-form-item>
        <el-form-item label="文本清洗">
          <el-switch v-model="createForm.clean_enabled" />
        </el-form-item>
        <el-form-item label="规则 JSON">
          <el-input
            v-model="createForm.rule_json"
            type="textarea"
            :rows="3"
            placeholder="可选，原样提交后端"
          />
        </el-form-item>
        <el-form-item label="数据集">
          <EvalDatasetUploader
            :reset-key="uploaderReset"
            :uploading="creating"
            :progress="uploadProgress"
            @change="(f) => (datasetFile = f)"
            @clear="datasetFile = null"
          />
          <p v-if="creating && createPhase" class="hint mt8">{{ createPhase }}</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 样本管理 -->
    <el-dialog v-model="sampleVisible" title="评测样本管理" width="760px" destroy-on-close>
      <div class="sample-toolbar">
        <el-input
          v-model="sampleKeyword"
          clearable
          placeholder="筛选问题/答案"
          style="width: 220px"
          @change="loadSamples"
        />
        <el-button type="primary" @click="openAddSample">新增样本</el-button>
      </div>
      <el-table :data="samples" max-height="360">
        <el-table-column prop="question" label="问题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="expected_answer" label="期望答案" min-width="180" show-overflow-tooltip />
        <el-table-column prop="tags" label="标签" width="100" />
      </el-table>
      <el-pagination
        class="mt12"
        v-model:current-page="samplePage"
        layout="prev, pager, next"
        :total="sampleTotal"
        @current-change="loadSamples"
      />
    </el-dialog>

    <!-- 样本录入 -->
    <el-dialog
      v-model="addSampleVisible"
      title="样本录入"
      width="520px"
      append-to-body
      @closed="persistSampleDraft"
    >
      <el-alert
        v-if="draftHint"
        type="info"
        :closable="false"
        show-icon
        class="mb12"
        :title="draftHint"
      />
      <el-form label-width="90px">
        <el-form-item label="问题">
          <el-input
            v-model="sampleForm.question"
            type="textarea"
            :rows="3"
            @input="scheduleDraftSave"
          />
          <p v-if="sampleInputTip" class="warn">{{ sampleInputTip }}</p>
        </el-form-item>
        <el-form-item label="期望答案">
          <el-input
            v-model="sampleForm.expected_answer"
            type="textarea"
            :rows="3"
            @input="scheduleDraftSave"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="sampleForm.tags" @input="scheduleDraftSave" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addSampleVisible = false">取消</el-button>
        <el-button @click="clearDraftAndForm">清空草稿</el-button>
        <el-button type="primary" :loading="sampleSaving" @click="submitSample">提交样本</el-button>
      </template>
    </el-dialog>

    <!-- 结果：表格 + 折线 + 单条详情 -->
    <el-dialog
      v-model="resultVisible"
      :title="resultTitle"
      width="920px"
      destroy-on-close
      top="5vh"
      @closed="disposeResultChart"
    >
      <div v-if="resultTask?.params" class="result-params muted mb12">
        知识库 {{ resultTask.params.kb_name || resultTask.params.kb_id }} ·
        {{ resultTask.params.embedding_model }} ·
        切分 {{ resultTask.params.chunk_size }}/{{ resultTask.params.chunk_overlap }}
      </div>

      <div ref="scoreChartRef" class="chart chart--sm" />

      <el-table :data="resultRows" max-height="280" class="mt12" @row-click="openDetail">
        <el-table-column prop="question" label="问题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="score" label="综合分" width="90">
          <template #default="{ row }">{{ fmtScore(row.score) }}</template>
        </el-table-column>
        <el-table-column prop="precision" label="精确率" width="90">
          <template #default="{ row }">{{ fmtScore(row.precision) }}</template>
        </el-table-column>
        <el-table-column prop="recall" label="召回率" width="90">
          <template #default="{ row }">{{ fmtScore(row.recall) }}</template>
        </el-table-column>
        <el-table-column prop="faithfulness" label="忠实度" width="90">
          <template #default="{ row }">{{ fmtScore(row.faithfulness) }}</template>
        </el-table-column>
        <el-table-column label="检索" width="130">
          <template #default="{ row }">
            <el-tag
              v-if="retrievalLabel(row)"
              :type="retrievalTagType(row)"
              size="small"
              effect="plain"
            >
              {{ retrievalLabel(row) }}
            </el-tag>
            <el-tag
              v-if="row.retrieval_degraded"
              type="warning"
              size="small"
              effect="plain"
              class="ml4"
            >
              已降级
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button text type="primary" @click.stop="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <p class="hint mt12">点击行可查看单条问答详情、参考片段与降级标识</p>
    </el-dialog>

    <!-- 单条问答详情 -->
    <el-drawer v-model="detailVisible" title="问答详情" size="480px" append-to-body>
      <template v-if="detailRow">
        <div class="detail-block">
          <div class="detail-label">问题</div>
          <div class="detail-body">{{ detailRow.question }}</div>
        </div>
        <div class="detail-block">
          <div class="detail-label">期望答案</div>
          <div class="detail-body">{{ detailRow.expected_answer || '—' }}</div>
        </div>
        <div class="detail-block">
          <div class="detail-label">模型回答</div>
          <div class="detail-body">{{ detailRow.answer || '—' }}</div>
        </div>
        <div class="detail-block">
          <div class="detail-label">指标</div>
          <div class="detail-metrics">
            <span>综合 {{ fmtScore(detailRow.score) }}</span>
            <span>精确 {{ fmtScore(detailRow.precision) }}</span>
            <span>召回 {{ fmtScore(detailRow.recall) }}</span>
            <span>忠实 {{ fmtScore(detailRow.faithfulness) }}</span>
          </div>
        </div>
        <div class="detail-block">
          <div class="detail-label">检索</div>
          <div>
            <el-tag
              v-if="retrievalLabel(detailRow)"
              :type="retrievalTagType(detailRow)"
              size="small"
              effect="plain"
            >
              {{ retrievalLabel(detailRow) }}
            </el-tag>
            <el-tag
              v-if="detailRow.retrieval_degraded"
              type="warning"
              size="small"
              effect="plain"
              class="ml4"
            >
              向量→关键词降级
            </el-tag>
            <span v-if="!retrievalLabel(detailRow) && !detailRow.retrieval_degraded" class="muted">
              —
            </span>
          </div>
        </div>
        <div v-if="detailRow.detail" class="detail-block">
          <div class="detail-label">说明</div>
          <div class="detail-body">{{ detailRow.detail }}</div>
        </div>
        <div class="detail-block">
          <div class="detail-label">参考片段</div>
          <div v-if="detailRow.sources?.length" class="source-list">
            <div v-for="(src, i) in detailRow.sources" :key="src.chunk_id || i" class="source-card">
              <div class="source-card__head">
                <span>{{ src.document_name || src.document_id || `片段 ${i + 1}` }}</span>
                <span v-if="src.score != null" class="muted">score {{ fmtScore(src.score) }}</span>
              </div>
              <pre>{{ src.content || '（无内容）' }}</pre>
            </div>
          </div>
          <div v-else class="muted">无参考片段</div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import {
  addEvalSample,
  createEvalTask,
  deleteEvalTask,
  fetchEvalCompare,
  fetchEvalProgress,
  fetchEvalResults,
  fetchEvalSamples,
  fetchEvalTasks,
  startEvalTask,
  uploadEvalDataset
} from '@/api/eval'
import { fetchKbIndexConfig } from '@/api/kbIndex'
import EvalDatasetUploader from '@/components/EvalDatasetUploader.vue'
import { useKbStore } from '@/stores/kb'
import { canSubmitInput, INPUT_MAX_LENGTH, processUserInput } from '@/utils/inputFilter'
import { buildEvalCacheScope } from '@/utils/cacheLifecycle'
import { clearEvalSamplesPreview, saveEvalSamplesPreview } from '@/utils/indexedDbCache'
import {
  clearEvalPendingCreate,
  clearEvalSampleDraft,
  loadEvalPageFilters,
  loadEvalPendingCreate,
  loadEvalSampleDraft,
  saveEvalPageFilters,
  saveEvalPendingCreate,
  saveEvalSampleDraft
} from '@/utils/localCache'
import {
  KB_CHUNK_SIZE_MIN,
  KB_CHUNK_SIZE_MAX,
  resolveKbIndexConfig
} from '@/utils/kbIndex'
import { useSplitStrategies } from '@/composables/useSplitStrategies'
import { embeddingModelNames, fetchRuntimeModelOptions } from '@/api/runtimeConfig'
import {
  getRetrievalModeLabel,
  retrievalModeTagType
} from '@/utils/retrievalMode'
import type { EvalComparePoint, EvalMetricRow, EvalSample, EvalTask } from '@/types'

const kbStore = useKbStore()

const loading = ref(false)
const tasks = ref<EvalTask[]>([])
const total = ref(0)

const cachedFilters = loadEvalPageFilters({
  status: '',
  keyword: '',
  page: 1,
  page_size: 10,
  compare_ids: [] as string[]
})
const page = ref(Number(cachedFilters.page) || 1)
const pageSize = ref(Number(cachedFilters.page_size) || 10)
const statusFilter = ref(String(cachedFilters.status || ''))
const keyword = ref(String(cachedFilters.keyword || ''))
const compareIds = ref<string[]>(
  Array.isArray(cachedFilters.compare_ids) ? cachedFilters.compare_ids.map(String) : []
)

const createVisible = ref(false)
const creating = ref(false)
const createPhase = ref('')
const uploadProgress = ref(0)
const uploaderReset = ref(0)
const datasetFile = ref<File | null>(null)
const kbLoading = ref(false)
const modelsLoading = ref(false)
const embeddingModels = ref<string[]>([])
const kbList = computed(() => (kbStore.list || []) as Array<{ id: string | number; name: string }>)

const {
  loading: splitLoading,
  error: splitError,
  items: splitItems,
  defaultItem: splitDefault,
  load: loadSplitStrategies,
  findByValue: findSplit
} = useSplitStrategies()

const chunkSizeMin = computed(
  () => findSplit(createForm.chunk_mode)?.chunk_size_min ?? KB_CHUNK_SIZE_MIN
)
const chunkSizeMax = computed(
  () => findSplit(createForm.chunk_mode)?.chunk_size_max ?? KB_CHUNK_SIZE_MAX
)

const createForm = reactive({
  name: '',
  kb_id: null as string | number | null,
  embedding_model: '',
  chunk_size: Number.NaN as number,
  chunk_overlap: Number.NaN as number,
  chunk_mode: '',
  separators: '',
  clean_enabled: true,
  rule_json: ''
})

function applySplitDefaults(strategyValue?: string) {
  const item = (strategyValue && findSplit(strategyValue)) || splitDefault.value
  if (!item) return
  createForm.chunk_mode = item.value
  createForm.chunk_size = item.default_chunk_size
  createForm.chunk_overlap = item.default_chunk_overlap
}

function onChunkModeChange(val: string) {
  const item = findSplit(val)
  if (!item) return
  createForm.chunk_size = item.default_chunk_size
  createForm.chunk_overlap = item.default_chunk_overlap
}

const sampleVisible = ref(false)
const currentTaskId = ref('')
const samples = ref<EvalSample[]>([])
const sampleTotal = ref(0)
const samplePage = ref(1)
const sampleKeyword = ref('')
const addSampleVisible = ref(false)
const sampleSaving = ref(false)
const sampleForm = reactive({ question: '', expected_answer: '', tags: '' })
const sampleInputTip = ref('')
const draftHint = ref('')
let draftTimer: ReturnType<typeof setTimeout> | null = null

const resultVisible = ref(false)
const resultTask = ref<EvalTask | null>(null)
const resultRows = ref<EvalMetricRow[]>([])
const resultTitle = computed(() =>
  resultTask.value ? `评测结果 · ${resultTask.value.name}` : '评测结果详情'
)

const detailVisible = ref(false)
const detailRow = ref<EvalMetricRow | null>(null)

const compareLoading = ref(false)
const comparePoints = ref<EvalComparePoint[]>([])
const metricGuideOpen = ref<string[]>([])
const lineChartRef = ref<HTMLDivElement | null>(null)
const scoreChartRef = ref<HTMLDivElement | null>(null)
let lineChart: echarts.ECharts | null = null
let scoreChart: echarts.ECharts | null = null

const runningId = ref('')
let progressTimer: ReturnType<typeof setInterval> | null = null

const compareTaskCols = computed(() =>
  Array.from(new Set(comparePoints.value.map((p) => p.task_name)))
)

const compareTable = computed(() => {
  const metrics = Array.from(new Set(comparePoints.value.map((p) => p.metric)))
  return metrics.map((metric) => {
    const row: Record<string, string | number> = { metric }
    for (const name of compareTaskCols.value) {
      const hit = comparePoints.value.find((p) => p.task_name === name && p.metric === metric)
      // value 可能是 number 或字符串，统一转数字后再格式化
      row[name] = hit ? Number(Number(hit.value).toFixed(3)) : '—'
    }
    return row
  })
})

/** 四项指标的静态说明（与后端词重叠计算口径对齐） */
const METRIC_GUIDE = [
  {
    key: 'score',
    label: '综合分',
    desc: '精确率与召回率的调和平均（F1），综合衡量「找得全」和「找得准」。',
    tip: '优先看这个；低于 0.4 通常说明期望答案与实际文本重合不足。'
  },
  {
    key: 'precision',
    label: '精确率',
    desc: '实际命中词里，有多少落在期望答案中。偏高表示答案更「干净」、少废话。',
    tip: '过低常见于回答过长、掺入大量无关词，或检索片段噪声大。'
  },
  {
    key: 'recall',
    label: '召回率',
    desc: '期望答案里的词，有多少被实际文本覆盖到。偏高表示要点覆盖更全。',
    tip: '单独很高、精确率却很低时，多半是「覆盖到了但混进很多杂质」。'
  },
  {
    key: 'faithfulness',
    label: '忠实度',
    desc: '当前实现为基于综合分的近似估计，反映回答相对期望要点的贴近程度。',
    tip: '用于辅助观察；与学术 RAG 忠实度不完全等同，对比任务时看相对高低即可。'
  }
] as const

const METRIC_CN: Record<string, string> = {
  score: '综合分',
  precision: '精确率',
  recall: '召回率',
  faithfulness: '忠实度'
}

function metricCn(key: unknown): string {
  const k = String(key || '')
  return METRIC_CN[k] || k
}

/** 根据当前对比数值生成一句可读结论 */
const compareInsight = computed(() => {
  if (!comparePoints.value.length) return null
  const avg = (metric: string) => {
    const vals = comparePoints.value
      .filter((p) => p.metric === metric)
      .map((p) => Number(p.value))
      .filter((n) => !Number.isNaN(n))
    if (!vals.length) return null
    return vals.reduce((a, b) => a + b, 0) / vals.length
  }
  const score = avg('score')
  const precision = avg('precision')
  const recall = avg('recall')
  if (score == null || precision == null || recall == null) return null

  let title = '本轮对比结论'
  let detail = ''
  if (recall >= 0.8 && precision < 0.35) {
    title = '召回高、精确率偏低'
    detail =
      '期望要点大多被覆盖到了，但答案或检索文本里无关词偏多，把精确率和综合分拉低。可尝试：收紧期望答案关键词、提高检索质量（向量/混合、开启 Rerank）、或检查切分是否过碎/过噪。'
  } else if (precision >= 0.6 && recall < 0.4) {
    title = '精确率尚可、召回不足'
    detail =
      '命中的词比较准，但期望答案里不少要点没命中。可检查样本期望是否写得过细，或检索/生成是否漏掉关键句。'
  } else if (score >= 0.6) {
    title = '整体表现较好'
    detail = `综合分约 ${score.toFixed(2)}，精确率 ${precision.toFixed(2)}、召回率 ${recall.toFixed(2)}。可继续用多任务对比验证切分或模型改动是否带来提升。`
  } else if (score < 0.35) {
    title = '整体偏低，建议先排查样本与检索'
    detail = `综合分约 ${score.toFixed(2)}。常见原因：期望答案与文档用语不一致、知识库未向量化完成、或检索降级为关键词导致语义问句命中差。建议先用命中测试单条验证，再重跑评测。`
  } else {
    title = '中等水平，仍有优化空间'
    detail = `综合分约 ${score.toFixed(2)}（精确率 ${precision.toFixed(2)} / 召回 ${recall.toFixed(2)}）。可对比不同切分参数或是否开启 Rerank，观察四项指标是否同步上升。`
  }
  return { title, detail }
})

function statusLabel(s: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[s] || s
}

function statusTag(s: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  if (s === 'completed') return 'success'
  if (s === 'running') return 'warning'
  if (s === 'failed') return 'danger'
  return 'info'
}

function fmtScore(v: number | undefined | null): string {
  if (v == null || Number.isNaN(Number(v))) return '—'
  return Number(v).toFixed(2)
}

function retrievalLabel(row: EvalMetricRow): string {
  return getRetrievalModeLabel(row.retrieval_mode || '')
}

function retrievalTagType(row: EvalMetricRow) {
  return retrievalModeTagType(row.retrieval_mode || '')
}

function persistFilters() {
  saveEvalPageFilters({
    status: statusFilter.value,
    keyword: keyword.value,
    page: page.value,
    page_size: pageSize.value,
    compare_ids: compareIds.value
  })
}

function onFilterChange() {
  page.value = 1
  persistFilters()
  loadTasks()
}

async function loadTasks() {
  loading.value = true
  persistFilters()
  try {
    let kw: string | undefined
    if (keyword.value) {
      const dual = processUserInput(keyword.value, 200)
      if (dual.blocked || dual.overLimit) {
        ElMessage.warning(dual.tip)
        return
      }
      kw = dual.raw
    }
    const data = await fetchEvalTasks({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
      keyword: kw
    })
    tasks.value = data.items || []
    total.value = data.total || 0
    ensureProgressPolling()
  } finally {
    loading.value = false
  }
}

async function loadKbAndModels() {
  kbLoading.value = true
  modelsLoading.value = true
  try {
    if (!kbStore.list.length) {
      await kbStore.loadList({ page: 1, page_size: 100 })
    } else {
      kbStore.loadList({ page: 1, page_size: 100 }).catch(() => {})
    }
  } finally {
    kbLoading.value = false
  }
  try {
    await loadSplitStrategies()
    if (!createForm.chunk_mode) applySplitDefaults()
  } catch {
    /* splitError 已展示 */
  }
  try {
    const data = await fetchRuntimeModelOptions()
    const list = embeddingModelNames(data)
    if (list.length) {
      embeddingModels.value = list
      if (!createForm.embedding_model || !list.includes(createForm.embedding_model)) {
        createForm.embedding_model = list[0]
      }
    } else {
      embeddingModels.value = []
      ElMessage.warning('后端未返回可用向量模型，请先在「大模型运行配置」配置')
    }
  } catch {
    embeddingModels.value = []
    ElMessage.error('拉取向量模型列表失败')
  } finally {
    modelsLoading.value = false
  }
}

async function onKbChange(kbId: string | number) {
  const kb = kbList.value.find((k) => String(k.id) === String(kbId))
  try {
    const config = await fetchKbIndexConfig(kbId)
    // 块参数以 index-config 为准；策略默认仍来自 split-strategies
    if (Number.isFinite(config.chunk_size)) createForm.chunk_size = config.chunk_size
    if (Number.isFinite(config.chunk_overlap)) createForm.chunk_overlap = config.chunk_overlap
  } catch {
    const { config } = resolveKbIndexConfig(kbId)
    if (Number.isFinite(config.chunk_size)) createForm.chunk_size = config.chunk_size
    if (Number.isFinite(config.chunk_overlap)) createForm.chunk_overlap = config.chunk_overlap
  }
  if (!createForm.chunk_mode) applySplitDefaults()
  if (kb && !createForm.name) {
    createForm.name = `${kb.name}-评测`
  }
}

function openCreate() {
  createForm.name = ''
  createForm.kb_id = kbStore.selectedKbId ?? null
  createForm.rule_json = ''
  datasetFile.value = null
  uploadProgress.value = 0
  uploaderReset.value += 1
  if (createForm.kb_id != null) onKbChange(createForm.kb_id)
  else {
    applySplitDefaults()
    createForm.separators = ''
    createForm.clean_enabled = true
    createForm.embedding_model = embeddingModels.value[0] || ''
  }
  createVisible.value = true
  loadKbAndModels()
}

function onCreateClosed() {
  uploadProgress.value = 0
  createPhase.value = ''
  datasetFile.value = null
}

/** 清理半完成创建留下的本地临时数据 */
async function clearCreateTempLocal(taskId?: string | null) {
  clearEvalPendingCreate()
  if (taskId) {
    clearEvalSampleDraft(taskId)
    try {
      await clearEvalSamplesPreview(buildEvalCacheScope(), taskId)
    } catch {
      /* ignore */
    }
  }
}

async function rollbackCreatedTask(taskId: string, reason: string) {
  try {
    await deleteEvalTask(taskId)
  } catch {
    ElMessage.error('数据集上传失败，且任务回滚删除未成功，请手动删除半完成任务')
  }
  await clearCreateTempLocal(taskId)
  uploadProgress.value = 0
  ElMessage.error(reason || '数据集上传失败，已回滚任务')
}

async function submitCreate() {
  if (creating.value) return

  const check = canSubmitInput(createForm.name, 80)
  if (!check.ok) {
    ElMessage.warning(check.tip)
    return
  }
  if (createForm.kb_id == null || createForm.kb_id === '') {
    ElMessage.warning('请选择知识库')
    return
  }
  if (!createForm.chunk_mode || !splitItems.value.some((s) => s.value === createForm.chunk_mode)) {
    ElMessage.warning('请选择后端下发的分块策略')
    return
  }
  if (!createForm.embedding_model) {
    ElMessage.warning('请选择向量模型')
    return
  }
  if (
    !Number.isFinite(createForm.chunk_size) ||
    !Number.isFinite(createForm.chunk_overlap) ||
    createForm.chunk_overlap >= createForm.chunk_size
  ) {
    ElMessage.warning('切片参数不合法：请先加载 split-strategies 默认值')
    return
  }

  // 事务前置：若选择了数据集，先校验文件可用，再进入创建（避免无效任务）
  const file = datasetFile.value
  if (file) {
    if (!file.size) {
      ElMessage.warning('数据集文件为空，请重新选择')
      return
    }
  }

  let ruleRaw: string | undefined
  if (createForm.rule_json) {
    const ruleDual = processUserInput(createForm.rule_json, INPUT_MAX_LENGTH)
    if (ruleDual.blocked || ruleDual.overLimit) {
      ElMessage.warning(ruleDual.tip)
      return
    }
    ruleRaw = ruleDual.raw
  }

  const kb = kbList.value.find((k) => String(k.id) === String(createForm.kb_id))
  const taskName = check.dual.raw.trim()

  creating.value = true
  createPhase.value = '正在创建任务…'
  uploadProgress.value = 0
  clearEvalPendingCreate()

  let createdId: string | null = null
  try {
    // 1) 创建任务
    const task = await createEvalTask({
      name: taskName,
      rule_json: ruleRaw,
      params: {
        kb_id: createForm.kb_id,
        kb_name: kb?.name,
        embedding_model: createForm.embedding_model,
        chunk_size: createForm.chunk_size,
        chunk_overlap: createForm.chunk_overlap,
        chunk_mode: createForm.chunk_mode,
        separators: createForm.separators,
        clean_enabled: createForm.clean_enabled
      }
    })
    createdId = task.id
    saveEvalPendingCreate(task.id, taskName)

    // 2) 有数据集则必须全部上传成功，否则回滚删除任务
    if (file) {
      createPhase.value = '正在上传数据集…'
      try {
        const imported = await uploadEvalDataset(task.id, file, (p) => {
          uploadProgress.value = p
        })
        if (uploadProgress.value < 100) uploadProgress.value = 100
        createPhase.value = '完成'
        clearEvalPendingCreate()
        ElMessage.success(`任务已创建，导入样本 ${imported?.imported ?? 0} 条`)
      } catch {
        await rollbackCreatedTask(task.id, '数据集上传失败，已回滚删除本次创建的任务')
        return
      }
    } else {
      clearEvalPendingCreate()
      ElMessage.success('任务已创建')
    }

    createVisible.value = false
    uploaderReset.value += 1
    datasetFile.value = null
    await loadTasks()
  } catch {
    // 创建本身失败：清本地半完成标记
    await clearCreateTempLocal(createdId)
    uploadProgress.value = 0
  } finally {
    creating.value = false
    createPhase.value = ''
  }
}

async function openSamples(row: EvalTask) {
  currentTaskId.value = row.id
  samplePage.value = 1
  sampleKeyword.value = ''
  sampleVisible.value = true
  await loadSamples()
}

async function loadSamples() {
  if (!currentTaskId.value) return
  let kw: string | undefined
  if (sampleKeyword.value) {
    const dual = processUserInput(sampleKeyword.value, 200)
    if (dual.blocked || dual.overLimit) {
      ElMessage.warning(dual.tip)
      return
    }
    kw = dual.raw
  }
  const data = await fetchEvalSamples(currentTaskId.value, {
    page: samplePage.value,
    page_size: 10,
    keyword: kw
  })
  samples.value = data.items || []
  sampleTotal.value = data.total || 0
  await saveEvalSamplesPreview(buildEvalCacheScope(), currentTaskId.value, samples.value)
}

function openAddSample() {
  const draft = loadEvalSampleDraft(currentTaskId.value)
  if (draft && (draft.question || draft.expected_answer || draft.tags)) {
    sampleForm.question = draft.question || ''
    sampleForm.expected_answer = draft.expected_answer || ''
    sampleForm.tags = draft.tags || ''
    draftHint.value = `已恢复未提交草稿（${draft.updated_at || ''}）`
  } else {
    sampleForm.question = ''
    sampleForm.expected_answer = ''
    sampleForm.tags = ''
    draftHint.value = '样本将先缓存在本地，提交成功后清除'
  }
  sampleInputTip.value = ''
  addSampleVisible.value = true
}

function scheduleDraftSave() {
  if (draftTimer) clearTimeout(draftTimer)
  draftTimer = setTimeout(() => persistSampleDraft(), 400)
}

function persistSampleDraft() {
  if (!currentTaskId.value) return
  if (!sampleForm.question && !sampleForm.expected_answer && !sampleForm.tags) return
  saveEvalSampleDraft(currentTaskId.value, { ...sampleForm })
}

function clearDraftAndForm() {
  clearEvalSampleDraft(currentTaskId.value)
  sampleForm.question = ''
  sampleForm.expected_answer = ''
  sampleForm.tags = ''
  draftHint.value = '草稿已清空'
  sampleInputTip.value = ''
}

async function submitSample() {
  const q = canSubmitInput(sampleForm.question, INPUT_MAX_LENGTH)
  if (!q.ok) {
    sampleInputTip.value = q.tip
    ElMessage.warning(q.tip)
    return
  }
  const a = canSubmitInput(sampleForm.expected_answer, INPUT_MAX_LENGTH)
  if (!a.ok) {
    sampleInputTip.value = a.tip
    ElMessage.warning(a.tip)
    return
  }
  sampleInputTip.value = ''
  let tagsRaw: string | undefined
  if (sampleForm.tags) {
    const tagsDual = processUserInput(sampleForm.tags, 200)
    if (tagsDual.blocked || tagsDual.overLimit) {
      sampleInputTip.value = tagsDual.tip
      ElMessage.warning(tagsDual.tip)
      return
    }
    tagsRaw = tagsDual.raw
  }
  sampleSaving.value = true
  try {
    await addEvalSample(currentTaskId.value, {
      question: q.dual.raw,
      expected_answer: a.dual.raw,
      tags: tagsRaw
    })
    clearEvalSampleDraft(currentTaskId.value)
    ElMessage.success('样本已提交')
    addSampleVisible.value = false
    sampleForm.question = ''
    sampleForm.expected_answer = ''
    sampleForm.tags = ''
    await loadSamples()
    await loadTasks()
  } finally {
    sampleSaving.value = false
  }
}

async function onRun(row: EvalTask) {
  if (row.status === 'running') return

  // 前置校验：无样本不发起启动请求
  let sampleLen = Number(row.sample_count) || 0
  try {
    const data = await fetchEvalSamples(row.id, { page: 1, page_size: 1 })
    sampleLen = Number(data?.total) || (data?.items?.length ?? 0) || sampleLen
  } catch {
    // 列表拉取失败时仍以任务上的 sample_count 为准
  }
  if (sampleLen <= 0) {
    await ElMessageBox.alert('当前任务样本数为 0，请先在「样本」中录入或导入数据集后再运行。', '无法运行评测', {
      type: 'warning',
      confirmButtonText: '知道了'
    })
    return
  }

  runningId.value = row.id
  try {
    await startEvalTask(row.id)
    ElMessage.success('评测已启动')
    await loadTasks()
  } catch {
    /* ignore */
  } finally {
    runningId.value = ''
  }
}

function ensureProgressPolling() {
  const hasRunning = tasks.value.some((t) => t.status === 'running')
  if (!hasRunning) {
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    return
  }
  if (progressTimer) return
  progressTimer = setInterval(async () => {
    const running = tasks.value.filter((t) => t.status === 'running')
    if (!running.length) {
      if (progressTimer) clearInterval(progressTimer)
      progressTimer = null
      return
    }
    await Promise.all(
      running.map(async (t) => {
        try {
          const p = await fetchEvalProgress(t.id)
          t.progress = p.progress
          t.status = p.status
          t.progress_message = p.message
        } catch {
          /* ignore */
        }
      })
    )
    if (!tasks.value.some((t) => t.status === 'running') && progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
      await loadTasks()
    }
  }, 1200)
}

async function openResults(row: EvalTask) {
  resultTask.value = row
  resultRows.value = await fetchEvalResults(row.id)
  resultVisible.value = true
  await nextTick()
  renderScoreChart()
}

function ensureChart(
  chart: echarts.ECharts | null,
  el: HTMLDivElement | null
): echarts.ECharts | null {
  if (!el) return null
  // 对话框/面板销毁后 DOM 会换新节点，旧实例必须重建，否则空白
  if (chart && chart.getDom() !== el) {
    chart.dispose()
    chart = null
  }
  return chart || echarts.init(el)
}

function renderScoreChart() {
  scoreChart = ensureChart(scoreChart, scoreChartRef.value)
  if (!scoreChart) return
  const labels = resultRows.value.map((r, i) => `#${i + 1}`)
  scoreChart.setOption({
    title: { text: '样本综合得分折线', left: 'center', textStyle: { fontSize: 13 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', min: 0, max: 1 },
    series: [
      {
        name: 'score',
        type: 'line',
        smooth: true,
        data: resultRows.value.map((r) => Number(r.score) || 0),
        areaStyle: { opacity: 0.08 }
      }
    ]
  })
}

function disposeResultChart() {
  scoreChart?.dispose()
  scoreChart = null
}

function openDetail(row: EvalMetricRow) {
  detailRow.value = row
  detailVisible.value = true
}

function toggleCompare(row: EvalTask) {
  const idx = compareIds.value.indexOf(row.id)
  if (idx >= 0) compareIds.value.splice(idx, 1)
  else compareIds.value.push(row.id)
  persistFilters()
}

function disposeLineChart() {
  lineChart?.dispose()
  lineChart = null
}

async function runCompare() {
  if (compareIds.value.length < 1) {
    ElMessage.warning('请先选择至少一个任务')
    return
  }
  compareLoading.value = true
  try {
    comparePoints.value = await fetchEvalCompare(compareIds.value)
    // 双 nextTick：等 v-if 挂上图表容器后再 init
    await nextTick()
    await nextTick()

    // 有结论时默认收起说明；无结论则展开（不依赖图表是否渲染成功）
    if (!metricGuideOpen.value.length && !compareInsight.value) {
      metricGuideOpen.value = ['guide']
    }

    lineChart = ensureChart(lineChart, lineChartRef.value)
    if (!lineChart) return

    const metrics = Array.from(new Set(comparePoints.value.map((p) => p.metric)))
    const names = Array.from(new Set(comparePoints.value.map((p) => p.task_name)))
    const metricLabels = metrics.map((m) => METRIC_CN[m] || m)
    const isDark = document.documentElement.classList.contains('admin-theme')
      && document.documentElement.getAttribute('data-color-mode') !== 'light'
    const axisColor = isDark ? 'rgba(210,210,215,0.72)' : '#64748b'
    const splitColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15,23,42,0.08)'
    lineChart.setOption(
      {
        color: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'],
        title: {
          text: '指标对比',
          left: 'center',
          textStyle: { fontSize: 13, fontWeight: 600, color: axisColor }
        },
        tooltip: {
          trigger: 'axis',
          valueFormatter: (v: number) => (v == null ? '—' : Number(v).toFixed(3))
        },
        legend: {
          bottom: 0,
          textStyle: { color: axisColor, fontSize: 12 }
        },
        grid: { left: 44, right: 16, top: 36, bottom: 44 },
        xAxis: {
          type: 'category',
          data: metricLabels,
          axisLabel: { color: axisColor, fontSize: 12 },
          axisLine: { lineStyle: { color: splitColor } }
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: 1,
          axisLabel: { color: axisColor, fontSize: 11 },
          splitLine: { lineStyle: { color: splitColor, type: 'dashed' } }
        },
        series: names.map((name) => ({
          name,
          type: 'line',
          smooth: false,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { width: 2.5 },
          data: metrics.map((m) => {
            const hit = comparePoints.value.find((p) => p.task_name === name && p.metric === m)
            return hit ? Number(Number(hit.value).toFixed(3)) : 0
          })
        }))
      },
      true
    )
    await nextTick()
    lineChart.resize()
  } finally {
    compareLoading.value = false
  }
}

watch(
  compareIds,
  (ids) => {
    persistFilters()
    // 取消全部对比后面板卸载，必须释放图表，否则再次对比会挂到已销毁 DOM
    if (!ids.length) {
      disposeLineChart()
      comparePoints.value = []
    }
  },
  { deep: true }
)

onMounted(async () => {
  // 上次创建中途崩溃留下的半完成标记：尝试回滚删除
  const pending = loadEvalPendingCreate()
  if (pending?.taskId) {
    try {
      await deleteEvalTask(pending.taskId)
    } catch {
      /* 任务可能已不存在 */
    }
    await clearCreateTempLocal(pending.taskId)
  }
  loadTasks()
  loadKbAndModels()
})

onBeforeUnmount(() => {
  if (progressTimer) clearInterval(progressTimer)
  if (draftTimer) clearTimeout(draftTimer)
  disposeLineChart()
  scoreChart?.dispose()
  scoreChart = null
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}
.table-footer {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.params-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.35;
}
.ops-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 8px;
}
.ops-cell :deep(.el-button) {
  margin: 0;
  padding: 0 2px;
}
.eval-task-table {
  width: 100%;
}
.muted {
  color: var(--admin-text-muted, #909399);
  font-size: 12px;
}
.panel {
  margin-top: 20px;
  padding: 18px 18px 14px;
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--glass-radius, 12px);
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.panel-head__text {
  min-width: 0;
}
.panel-title {
  font-weight: 600;
  font-size: 16px;
  line-height: 1.4;
}
.panel-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--admin-text-muted, #909399);
  line-height: 1.4;
}
.insight-banner {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 28%, transparent);
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
}
.insight-banner__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color-primary, inherit);
  margin-bottom: 6px;
}
.insight-banner__detail {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-color-regular, var(--admin-text-muted, #606266));
}
.compare-body {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(220px, 0.9fr);
  gap: 14px 18px;
  align-items: stretch;
  margin-bottom: 8px;
}
.compare-empty {
  padding: 28px 12px;
  text-align: center;
  font-size: 13px;
}
.compare-table {
  width: 100%;
  align-self: center;
}
.metric-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.3;
}
.metric-cell__cn {
  font-weight: 600;
  font-size: 13px;
}
.metric-cell__en {
  font-size: 11px;
  color: var(--admin-text-muted, #909399);
}
.metric-collapse {
  margin-top: 8px;
  border: none;
  --el-collapse-header-height: 42px;
}
.metric-collapse :deep(.el-collapse-item__header) {
  background: transparent;
  border: none;
  color: var(--text-color-secondary, inherit);
  font-size: 13px;
  padding-left: 0;
}
.metric-collapse :deep(.el-collapse-item__wrap) {
  background: transparent;
  border: none;
}
.metric-collapse :deep(.el-collapse-item__content) {
  padding: 4px 0 8px;
}
.metric-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
}
.metric-list__row {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--glass-border, #ccc) 70%, transparent);
  background: color-mix(in srgb, var(--el-color-primary) 5%, transparent);
}
.metric-list__row:last-child {
  /* 两列布局下保留统一卡片样式 */
  padding-bottom: 12px;
}
.metric-list__label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.metric-list__cn {
  font-weight: 600;
  font-size: 13px;
}
.metric-list__label code {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--el-color-primary) 14%, transparent);
  color: var(--el-color-primary);
}
.metric-list__desc,
.metric-list__tip {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
}
.metric-list__desc {
  color: var(--text-color-regular, inherit);
}
.metric-list__tip {
  margin-top: 6px !important;
  color: var(--admin-text-muted, #909399);
}
.metric-foot {
  margin: 12px 0 0;
  font-size: 12px;
  line-height: 1.5;
}
.chart {
  width: 100%;
  height: 280px;
  margin-top: 8px;
}
.chart--compare {
  height: 260px;
  margin-top: 0;
  min-height: 220px;
}
@media (max-width: 960px) {
  .compare-body {
    grid-template-columns: 1fr;
  }
  .chart--compare {
    height: 240px;
  }
  .metric-list {
    grid-template-columns: 1fr;
  }
}
.chart--sm {
  height: 220px;
}
.sample-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.mt12 {
  margin-top: 12px;
}
.mt8 {
  margin-top: 8px;
}
.mb12 {
  margin-bottom: 12px;
}
.ml4 {
  margin-left: 4px;
}
.warn {
  margin: 4px 0 0;
  color: var(--el-color-warning);
  font-size: 12px;
}
.hint {
  font-size: 12px;
  color: var(--admin-text-muted, #909399);
}
.result-params {
  line-height: 1.5;
}
.detail-block {
  margin-bottom: 16px;
}
.detail-label {
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--admin-text-muted, #909399);
}
.detail-body {
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
.detail-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
}
.source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.source-card {
  padding: 8px 10px;
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.12));
  border-radius: 8px;
  background: rgba(10, 18, 36, 0.18);
}
.source-card__head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}
.source-card pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.45;
  font-family: inherit;
}
</style>
