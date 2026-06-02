<template>
  <div class="kg-page">
    <el-card class="kg-toolbar">
      <el-form :model="filter" inline>
        <el-form-item label="科目">
          <el-select v-model="filter.subject_id" placeholder="全部" clearable style="width:140px" @change="fetchGraph">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="filter.keyword" placeholder="搜索实体或关系..." clearable style="width:200px" @keyup.enter="handleSearch" @clear="handleClearSearch" />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchGraph">刷新图谱</el-button>
          <el-button type="primary" @click="showAddNode">+ 手动添加</el-button>
          <el-button type="success" @click="showAddEdge">添加关系</el-button>
          <el-button type="warning" @click="showGenerateDoc">生成文档</el-button>
          <el-button @click="openCandidateDrawer">候选关系审核</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="rebuildStatus.status !== 'not_started'" class="rebuild-status">
      <div class="rebuild-summary">
        <span class="rebuild-title">图谱全量重建</span>
        <el-tag :type="rebuildTagType">{{ rebuildStatusLabel }}</el-tag>
        <span class="rebuild-progress">
          {{ rebuildStatus.completed_documents || 0 }} / {{ rebuildStatus.total_documents || 0 }} 个文档完成
        </span>
        <span v-if="rebuildStatus.failed_documents" class="rebuild-failed">
          {{ rebuildStatus.failed_documents }} 个失败
        </span>
        <el-button
          v-if="rebuildStatus.failed_documents"
          size="small"
          type="warning"
          :loading="retryingRebuild"
          @click="handleRetryFailedRebuild"
        >重试失败文档</el-button>
      </div>
      <el-progress
        :percentage="rebuildPercentage"
        :status="rebuildStatus.status === 'partial_failed' ? 'warning' : undefined"
        :stroke-width="6"
      />
    </el-card>

    <div class="kg-body">
      <div class="graph-wrapper">
        <el-card class="graph-container" v-loading="loading">
          <div ref="graphRef" class="graph-canvas"></div>
          <el-empty v-if="!loading && graphData.nodes.length === 0" description="暂无图谱数据，请先导入种子数据" />
          <div class="graph-hint">滚轮缩放 · 拖拽平移 · 点击节点查看详情</div>
        </el-card>
        <div class="graph-legend">
          <div class="legend-title">关系</div>
          <div v-for="(cfg, type) in edgeTypeConfig" :key="type" class="legend-item">
            <span class="legend-dot" :style="{ background: cfg.color }"></span>
            <span class="legend-label">{{ cfg.label }}</span>
          </div>
        </div>
      </div>
      <el-card class="detail-panel">
        <template #header>
          <span>{{ selectedNode ? '节点详情' : '图谱信息' }}</span>
        </template>
        <div v-if="selectedNode">
          <div class="detail-name">{{ selectedNode.label }}</div>
          <div class="detail-row"><span class="detail-key">ID</span><span class="detail-val">{{ selectedNode.id }}</span></div>
          <div class="detail-row"><span class="detail-key">科目</span><span class="detail-val">{{ subjectName(selectedNode.group) }}</span></div>
          <div v-if="nodeRelations.length" class="detail-rels">
            <div class="detail-rels-title">关联节点</div>
            <div v-for="rel in nodeRelations" :key="rel.id" class="rel-item">
              <span class="rel-dot" :style="{ background: edgeTypeConfig[rel.relation_type]?.color || '#999' }"></span>
              <span class="rel-text">{{ rel.target_name }}</span>
              <span class="rel-type">{{ edgeTypeConfig[rel.relation_type]?.label || rel.relation_type }}</span>
            </div>
          </div>
          <div class="detail-actions">
            <el-button size="small" @click="editNode(selectedNode)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeleteNode(selectedNode.id)">删除</el-button>
          </div>
        </div>
        <div v-else>
          <div class="stat-item"><span class="stat-num">{{ graphData.nodes.length }}</span><span class="stat-label">节点数</span></div>
          <div class="stat-item"><span class="stat-num">{{ graphData.edges.length }}</span><span class="stat-label">关系数</span></div>
          <div v-if="filter.keyword && highlightedNodes.size" class="stat-item" style="color:#f59e0b">
            <span class="stat-num" style="color:#f59e0b">{{ highlightedNodes.size }}</span><span class="stat-label">匹配节点</span>
          </div>
          <p v-if="!filter.keyword" style="color:#94a3b8;font-size:12px;margin-top:12px">选择节点查看详情</p>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="nodeDialog" :title="isEditNode ? '编辑节点' : '添加节点'" width="450px">
      <el-form ref="nodeFormRef" :model="nodeForm" :rules="nodeRules" label-width="70px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="nodeForm.name" />
        </el-form-item>
        <el-form-item label="科目" prop="subject_id">
          <el-select v-model="nodeForm.subject_id" style="width:100%">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-rate v-model="nodeForm.difficulty" :max="5" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="nodeForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nodeDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveNode">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="genDocDialog" title="从知识图谱生成文档" width="450px">
      <el-form :model="genDocForm" label-width="80px">
        <el-form-item label="科目">
          <el-select v-model="genDocForm.subject_id" style="width:100%" placeholder="请选择科目">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文档类型">
          <el-select v-model="genDocForm.doc_type" style="width:100%">
            <el-option label="学习指南" value="study_guide" />
            <el-option label="考试试卷" value="exam_paper" />
            <el-option label="知识总结" value="summary" />
            <el-option label="教学大纲" value="outline" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="genDocDialog = false">取消</el-button>
        <el-button type="primary" :loading="genDocLoading" @click="handleGenerateDoc">开始生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="edgeDialog" title="添加关系" width="450px">
      <el-form :model="edgeForm" label-width="90px">
        <el-form-item label="源节点">
          <el-select v-model="edgeForm.source_id" filterable style="width:100%">
            <el-option v-for="n in graphData.nodes" :key="n.id" :label="n.label" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标节点">
          <el-select v-model="edgeForm.target_id" filterable style="width:100%">
            <el-option v-for="n in graphData.nodes" :key="n.id" :label="n.label" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关系类型">
          <el-select v-model="edgeForm.relation_type" style="width:100%">
            <el-option label="前置条件" value="PREREQUISITE" />
            <el-option label="后继" value="NEXT" />
            <el-option label="关联" value="RELATED" />
            <el-option label="包含" value="CONTAINS" />
            <el-option label="对比" value="CONTRAST" />
            <el-option label="考点" value="EXAMINED_IN" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="edgeForm.description" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="edgeDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveEdge">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="candidateDrawer" title="候选关系审核" size="520px">
      <div v-loading="candidateLoading">
        <el-empty v-if="!candidateLoading && !candidates.length" description="暂无待审核候选关系" />
        <el-card v-for="candidate in candidates" :key="candidate.id" class="candidate-card">
          <div class="candidate-title">
            <b>{{ candidate.source_name }}</b>
            <span>→</span>
            <b>{{ candidate.target_name }}</b>
          </div>
          <div class="candidate-meta">
            <el-tag size="small">{{ edgeTypeConfig[candidate.relation_type]?.label || candidate.relation_type }}</el-tag>
            <span>置信度 {{ (candidate.confidence * 100).toFixed(0) }}%</span>
          </div>
          <p>{{ candidate.description || '暂无关系说明' }}</p>
          <div class="candidate-evidence">证据：{{ candidate.evidence_text || '暂无证据文本' }}</div>
          <div class="candidate-source">来源：{{ candidate.document_title || '未知文档' }}</div>
          <div class="candidate-actions">
            <el-button size="small" type="primary" @click="reviewCandidate(candidate.id, true)">批准入图</el-button>
            <el-button size="small" type="danger" plain @click="reviewCandidate(candidate.id, false)">驳回</el-button>
          </div>
        </el-card>
        <el-pagination
          v-if="candidateTotal > candidateSize"
          layout="prev, pager, next"
          :total="candidateTotal"
          :page-size="candidateSize"
          v-model:current-page="candidatePage"
          @current-change="fetchCandidates"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, onActivated, onDeactivated, nextTick } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { Network } from 'vis-network'
import 'vis-network/styles/vis-network.css'
import { getSubgraph, searchSubgraph, createPoint, updatePoint, deletePoint, createRelation, generateDocument, getRebuildStatus, retryFailedRebuildDocuments, getRelationCandidates, approveRelationCandidate, rejectRelationCandidate } from '@/api/kg'
import { getSubjects } from '@/api/subjects'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

const graphRef = ref(null)
const loading = ref(false)
const subjects = ref([])
const filter = ref({ subject_id: null, keyword: '' })
const graphData = ref({ nodes: [], edges: [] })
const selectedNode = ref(null)
const highlightedNodes = ref(new Set())
const isSearchMode = ref(false)
const nodeRelations = ref([])
const rebuildStatus = ref({ status: 'not_started', total_documents: 0, completed_documents: 0, failed_documents: 0 })
const retryingRebuild = ref(false)
const candidateDrawer = ref(false)
const candidateLoading = ref(false)
const candidates = ref([])
const candidatePage = ref(1)
const candidateSize = 20
const candidateTotal = ref(0)
let network = null
let renderedGraphSignature = ''

const edgeTypeConfig = {
  PREREQUISITE: { color: '#f472b6', dashes: 'dashed', label: '前置条件' },
  NEXT:         { color: '#38bdf8', dashes: 'solid',  label: '后继' },
  RELATED:      { color: '#a78bfa', dashes: 'solid',  label: '关联' },
  CONTAINS:     { color: '#4ade80', dashes: 'dotted', label: '包含' },
  CONTRAST:     { color: '#fbbf24', dashes: 'dashed', label: '对比' },
  EXAMINED_IN:  { color: '#fb923c', dashes: 'dotted', label: '考点' },
}

const nodeDialog = ref(false)
const isEditNode = ref(false)
const saving = ref(false)
const nodeFormRef = ref(null)
const nodeForm = ref({ name: '', subject_id: null, difficulty: 3, description: '' })
const nodeRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  subject_id: [{ required: true, message: '请选择科目', trigger: 'change' }],
}

const edgeDialog = ref(false)
const edgeForm = ref({ source_id: null, target_id: null, relation_type: 'RELATED', description: '' })

const genDocDialog = ref(false)
const genDocLoading = ref(false)
const genDocForm = ref({ subject_id: null, doc_type: 'study_guide' })

const { refresh: autoRefresh, stopPolling: stopAutoRefresh, startPolling: startAutoRefresh } = useAutoRefresh(() => {
  fetchRebuildStatus()
  if (!isSearchMode.value && graphData.value.nodes.length > 0) {
    fetchGraph(true)
  }
}, 30000)

onMounted(() => {
  fetchSubjects()
  fetchGraph()
  fetchRebuildStatus()
  window.addEventListener('resize', handleResize)
})

const rebuildPercentage = computed(() => {
  const total = rebuildStatus.value.total_documents || 0
  return total ? Math.round(((rebuildStatus.value.completed_documents || 0) / total) * 100) : 0
})

const rebuildStatusLabel = computed(() => ({
  queued: '排队中',
  running: '重建中',
  success: '已完成',
  partial_failed: '部分失败',
  failed: '失败',
}[rebuildStatus.value.status] || '未开始'))

const rebuildTagType = computed(() => ({
  queued: 'info',
  running: 'primary',
  success: 'success',
  partial_failed: 'warning',
  failed: 'danger',
}[rebuildStatus.value.status] || 'info'))

async function fetchRebuildStatus() {
  try {
    const res = await getRebuildStatus()
    if (res.code === 200) rebuildStatus.value = res.data
  } catch {}
}

async function handleRetryFailedRebuild() {
  retryingRebuild.value = true
  try {
    const res = await retryFailedRebuildDocuments()
    if (res.code === 200) {
      ElMessage.success(`已重新排队 ${res.data.queued_documents} 个文档`)
      await fetchRebuildStatus()
    }
  } finally {
    retryingRebuild.value = false
  }
}

async function openCandidateDrawer() {
  candidateDrawer.value = true
  candidatePage.value = 1
  await fetchCandidates()
}

async function fetchCandidates() {
  candidateLoading.value = true
  try {
    const res = await getRelationCandidates({ status: 'pending', page: candidatePage.value, size: candidateSize })
    if (res.code === 200) {
      candidates.value = res.data.items || []
      candidateTotal.value = res.data.total || 0
    }
  } finally {
    candidateLoading.value = false
  }
}

async function reviewCandidate(id, approved) {
  if (approved) await approveRelationCandidate(id)
  else await rejectRelationCandidate(id)
  ElMessage.success(approved ? '候选关系已批准' : '候选关系已驳回')
  await fetchCandidates()
  if (approved) fetchGraph()
}

onActivated(() => {
  if (graphData.value.nodes.length > 0) autoRefresh()
})

onDeactivated(() => {
  stopAutoRefresh()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (network) network.destroy()
})

function handleResize() {
  if (network && graphRef.value) network.fit({ animation: false })
}

async function fetchSubjects() {
  try {
    const res = await getSubjects()
    if (res.code === 200) {
      subjects.value = res.data.map(s => ({ id: s.id, name: s.name }))
    } else {
      ElNotification.error({ title: '获取科目列表失败', message: res.message || '未知错误' })
    }
  } catch (error) {
    ElNotification.error({ title: '获取科目列表失败', message: error.message || '网络异常' })
  }
}

async function fetchGraph(silent = false) {
  if (!silent) loading.value = true
  try {
    const params = {}
    if (filter.value.subject_id) params.subject_id = filter.value.subject_id

    const keyword = filter.value.keyword.trim()
    if (keyword) {
      isSearchMode.value = true
      const res = await searchSubgraph({ keyword, ...params })
      if (res.code === 200) {
        if (res.data.error) throw new Error(res.data.error)
        const data = { nodes: res.data.nodes || [], edges: res.data.edges || [] }
        highlightedNodes.value = new Set(data.nodes.map(node => node.id))
        graphData.value = data
      }
    } else {
      isSearchMode.value = false
      highlightedNodes.value = new Set()
      const res = await getSubgraph(params)
      if (res.code === 200) {
        if (res.data.error) throw new Error(res.data.error)
        graphData.value = { nodes: res.data.nodes || [], edges: res.data.edges || [] }
      }
    }
    syncSelectedNode()
    await nextTick()
    await new Promise(r => requestAnimationFrame(r))
    renderGraph(silent)
  } catch (error) {
    if (!silent) ElMessage.error('获取图谱失败：' + (error.message || '网络异常'))
  } finally {
    if (!silent) loading.value = false
  }
}

// ── Macaron pastel palette: soft, modern, minimalist ──
const GROUP_COLORS = [
  { bg: '#f0f9ff', border: '#38bdf8', highlight: '#bae6fd', text: '#0369a1' },   // sky
  { bg: '#fdf2f8', border: '#f472b6', highlight: '#fbcfe8', text: '#be185d' },   // pink
  { bg: '#f0fdf4', border: '#4ade80', highlight: '#bbf7d0', text: '#15803d' },   // emerald
  { bg: '#fffbeb', border: '#fbbf24', highlight: '#fde68a', text: '#b45309' },   // amber
  { bg: '#faf5ff', border: '#a78bfa', highlight: '#ddd6fe', text: '#6d28d9' },   // violet
  { bg: '#f0fdfa', border: '#2dd4bf', highlight: '#a7f3d0', text: '#0f766e' },   // teal
  { bg: '#fff1f2', border: '#fb7185', highlight: '#fecdd3', text: '#be123c' },   // rose
  { bg: '#fefce8', border: '#eab308', highlight: '#fef08a', text: '#854d0e' },   // yellow
]

function getGroupColor(group) {
  return GROUP_COLORS[parseInt(group) % GROUP_COLORS.length] || GROUP_COLORS[0]
}

function getEdgeStyle(type) {
  const cfg = edgeTypeConfig[type] || { color: '#94a3b8', dashes: 'solid' }
  return {
    color: cfg.color,
    dashes: cfg.dashes === 'dashed' ? [10, 6] : cfg.dashes === 'dotted' ? [3, 6] : false,
    opacity: 0.7,
  }
}

function computeDegree() {
  const deg = {}
  for (const e of graphData.value.edges) {
    deg[e.from] = (deg[e.from] || 0) + 1
    deg[e.to] = (deg[e.to] || 0) + 1
  }
  return deg
}

function graphSignature() {
  return JSON.stringify({
    nodes: graphData.value.nodes.map(n => [n.id, n.label, n.group]),
    edges: graphData.value.edges.map(e => [e.from, e.to, e.label, e.title]),
  })
}

function destroyNetwork() {
  if (network) network.destroy()
  network = null
  renderedGraphSignature = ''
}

function syncSelectedNode() {
  const selectedId = selectedNode.value?.id
  if (!selectedId) return
  const node = graphData.value.nodes.find(item => String(item.id) === String(selectedId))
  if (!node) {
    selectedNode.value = null
    nodeRelations.value = []
    return
  }
  selectedNode.value = node
  nodeRelations.value = relationsForNode(selectedId)
}

function relationsForNode(nodeId) {
  const relations = []
  for (const edge of graphData.value.edges) {
    if (String(edge.from) === String(nodeId)) {
      const target = graphData.value.nodes.find(node => String(node.id) === String(edge.to))
      if (target) relations.push({ id: nodeId + '-' + edge.to, target_name: target.label, relation_type: edge.label })
    }
    if (String(edge.to) === String(nodeId)) {
      const source = graphData.value.nodes.find(node => String(node.id) === String(edge.from))
      if (source) relations.push({ id: edge.from + '-' + nodeId, target_name: source.label, relation_type: edge.label })
    }
  }
  return relations
}

function subjectName(group) {
  return subjects.value.find(subject => String(subject.id) === String(group))?.name || group || '未知'
}

function renderGraph(silent = false) {
  if (!graphRef.value) return
  if (!graphData.value.nodes.length) {
    destroyNetwork()
    return
  }

  const signature = graphSignature()
  if (silent && signature === renderedGraphSignature) return
  renderedGraphSignature = signature

  const hl = highlightedNodes.value
  const degree = computeDegree()
  const maxDeg = Math.max(1, ...Object.values(degree))

  const nodes = graphData.value.nodes.map(n => {
    const isHl = hl.size && hl.has(n.id)
    const colors = getGroupColor(n.group || '0')
    const nodeDeg = degree[n.id] || 0
    const scaledSize = 28 + Math.round((nodeDeg / maxDeg) * 28)

    return {
      id: n.id,
      label: n.label,
      group: n.group || '0',
      title: '<div style="padding:8px 12px;font-size:13px;line-height:1.6"><b style="color:#334155">' + n.label + '</b><br/><span style="color:#94a3b8;font-size:12px">关联 ' + nodeDeg + ' 个节点</span></div>',
      size: isHl ? Math.max(scaledSize + 6, 44) : scaledSize,
      font: {
        size: isHl ? 13 : (scaledSize > 42 ? 13 : 11),
        color: colors.text,
        face: "'PingFang SC','Microsoft YaHei','Helvetica Neue',Arial,sans-serif",
        strokeWidth: 2,
        strokeColor: '#ffffff',
        bold: isHl ? true : false,
      },
      borderWidth: isHl ? 3 : 2,
      borderWidthSelected: 3.5,
      color: isHl
        ? {
            background: '#fffbeb',
            border: '#f59e0b',
            highlight: { background: '#fef3c7', border: '#d97706' },
            hover: { background: '#fffbeb', border: '#f59e0b' },
          }
        : {
            background: colors.bg,
            border: colors.border,
            highlight: { background: colors.bg, border: colors.border },
            hover: { background: colors.highlight, border: colors.border },
          },
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.06)',
        size: 14,
        x: 0,
        y: 3,
      },
      shape: 'dot',
      mass: 1 + nodeDeg * 0.2,
    }
  })

  const edges = graphData.value.edges.map(e => {
    const style = getEdgeStyle(e.label)
    return {
      from: e.from,
      to: e.to,
      label: edgeTypeConfig[e.label]?.label || e.label,
      title: e.title || e.label,
      arrows: { to: { enabled: true, scaleFactor: 0.6, type: 'arrow' } },
      font: {
        size: 10,
        color: style.color,
        face: "'PingFang SC','Microsoft YaHei',Arial,sans-serif",
        align: 'middle',
        strokeWidth: 2,
        strokeColor: '#ffffff',
        background: 'rgba(255,255,255,0.7)',
      },
      smooth: { type: 'curvedCW', roundness: 0.15 },
      color: { color: style.color, highlight: style.color, hover: style.color, opacity: style.opacity },
      width: 1.5,
      dashes: style.dashes,
      selectionWidth: 2.5,
      hoverWidth: 2.5,
    }
  })

  const container = graphRef.value
  const options = {
    autoResize: false,
    backgroundColor: 'transparent',
    physics: {
      enabled: true,
      stabilization: { iterations: 200, updateInterval: 20 },
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -1500,
        centralGravity: 0.001,
        springLength: 500,
        springConstant: 0.005,
        damping: 0.4,
        avoidOverlap: 1,
      },
      maxVelocity: 15,
      minVelocity: 0.1,
      timestep: 0.35,
      wind: { x: 0, y: 0 },
    },
    interaction: {
      hover: true,
      tooltipDelay: 150,
      selectConnectedEdges: true,
      multiselect: false,
      navigationButtons: true,
      keyboard: true,
      zoomView: true,
      dragView: true,
    },
    layout: { improvedLayout: true, randomSeed: 42 },
    edges: {
      color: 'rgba(148,163,184,0.3)',
      width: 1,
      smooth: { type: 'curvedCW', roundness: 0.15 },
    },
    groups: {},
    nodes: {
      shape: 'dot',
      size: 28,
      font: {
        size: 11,
        color: '#475569',
        face: "'PingFang SC','Microsoft YaHei','Helvetica Neue',Arial,sans-serif",
        strokeWidth: 2,
        strokeColor: '#ffffff',
      },
      borderWidth: 2,
      borderWidthSelected: 3.5,
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.06)',
        size: 14,
        x: 0,
        y: 3,
      },
    },
  }

  if (network) { network.destroy(); network = null }
  network = new Network(container, { nodes, edges }, options)

  // After physics settles: freeze, fit view, lock canvas boundaries
  network.once('stabilizationIterationsDone', () => {
    network.setOptions({ physics: { enabled: false } })
    network.fit({ animation: false })

    const PAD = 300
    const allPos = network.getPositions()
    let bxMin = Infinity, byMin = Infinity, bxMax = -Infinity, byMax = -Infinity
    for (const id of Object.keys(allPos)) {
      const p = allPos[id]
      if (p.x < bxMin) bxMin = p.x
      if (p.y < byMin) byMin = p.y
      if (p.x > bxMax) bxMax = p.x
      if (p.y > byMax) byMax = p.y
    }
    const canvasBounds = {
      minX: bxMin - PAD, minY: byMin - PAD,
      maxX: bxMax + PAD, maxY: byMax + PAD,
    }

    function clampView() {
      const scale = network.getScale()
      const pos = network.getViewPosition()
      const halfW = container.clientWidth / 2 / scale
      const halfH = container.clientHeight / 2 / scale
      let cx = pos.x, cy = pos.y
      let moved = false
      if (cx - halfW < canvasBounds.minX) { cx = canvasBounds.minX + halfW; moved = true }
      if (cx + halfW > canvasBounds.maxX) { cx = canvasBounds.maxX - halfW; moved = true }
      if (cy - halfH < canvasBounds.minY) { cy = canvasBounds.minY + halfH; moved = true }
      if (cy + halfH > canvasBounds.maxY) { cy = canvasBounds.maxY - halfH; moved = true }
      if (moved) network.moveTo({ position: { x: cx, y: cy }, animation: false })
    }

    network.on('dragEnd', clampView)
    network.on('zoom', clampView)
  })

  network.on('click', (params) => {
    if (params.nodes.length) {
      const nodeId = params.nodes[0]
      const node = graphData.value.nodes.find(n => n.id === nodeId)
      selectedNode.value = node || null
      nodeRelations.value = node ? relationsForNode(nodeId) : []
    } else {
      selectedNode.value = null
      nodeRelations.value = []
    }
  })

  network.on('doubleClick', () => { fitGraph() })
}

function fitGraph() {
  if (!network) return
  if (isSearchMode.value && highlightedNodes.value.size) {
    const ids = Array.from(highlightedNodes.value)
    network.fit({
      animation: false,
      nodes: ids,
    })
  } else {
    network.fit({
      animation: false,
    })
  }
}

async function handleSearch() {
  filter.value.keyword = filter.value.keyword.trim()
  if (filter.value.keyword) {
    await fetchGraph()
    if (highlightedNodes.value.size) {
      fitGraph()
    } else {
      ElMessage.info('未找到匹配的实体')
    }
  }
}

function handleClearSearch() {
  filter.value.keyword = ''
  highlightedNodes.value = new Set()
  isSearchMode.value = false
  fetchGraph()
}

function showAddNode() {
  isEditNode.value = false
  nodeForm.value = { name: '', subject_id: filter.value.subject_id || null, difficulty: 3, description: '' }
  nodeDialog.value = true
}

function editNode(node) {
  isEditNode.value = true
  nodeForm.value = {
    name: node.label,
    subject_id: parseInt(node.group) || null,
    difficulty: 3,
    description: '',
  }
  nodeForm.value._id = node.id
  nodeDialog.value = true
}

async function handleSaveNode() {
  const valid = await nodeFormRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEditNode.value) {
      await updatePoint(nodeForm.value._id, nodeForm.value)
      ElMessage.success('更新成功')
    } else {
      await createPoint(nodeForm.value)
      ElMessage.success('创建成功')
    }
    nodeDialog.value = false
    fetchGraph()
  } finally {
    saving.value = false
  }
}

async function handleDeleteNode(id) {
  try {
    await deletePoint(id)
    ElMessage.success('已删除')
    selectedNode.value = null
    nodeRelations.value = []
    fetchGraph()
  } catch {}
}

function showGenerateDoc() {
  genDocForm.value = { subject_id: filter.value.subject_id, doc_type: 'study_guide' }
  genDocDialog.value = true
}

async function handleGenerateDoc() {
  if (!genDocForm.value.subject_id) {
    ElMessage.warning('请选择科目')
    return
  }
  genDocLoading.value = true
  try {
    const res = await generateDocument(genDocForm.value)
    if (res.code === 200) {
      ElMessage.success('文档生成成功，正在解析中...')
      genDocDialog.value = false
    } else {
      ElMessage.error(res.message || '生成失败')
    }
  } catch {
    ElMessage.error('生成失败，请重试')
  } finally {
    genDocLoading.value = false
  }
}

function showAddEdge() {
  edgeForm.value = { source_id: null, target_id: null, relation_type: 'RELATED', description: '' }
  edgeDialog.value = true
}

async function handleSaveEdge() {
  if (!edgeForm.value.source_id || !edgeForm.value.target_id) {
    ElMessage.warning('请选择源节点和目标节点')
    return
  }
  if (String(edgeForm.value.source_id) === String(edgeForm.value.target_id)) {
    ElMessage.warning('源节点和目标节点不能相同')
    return
  }
  saving.value = true
  try {
    await createRelation(edgeForm.value)
    ElMessage.success('关系已创建')
    edgeDialog.value = false
    fetchGraph()
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.kg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  overflow: hidden;
}

.kg-toolbar {
  flex-shrink: 0;
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  border-radius: 10px;
}
.kg-toolbar .el-form { margin-bottom: 0; }

.rebuild-status {
  flex-shrink: 0;
  border: none;
  border-radius: 10px;
}
.rebuild-status :deep(.el-card__body) { padding: 10px 16px; }
.rebuild-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #64748b;
}
.rebuild-title { font-weight: 700; color: #334155; }
.rebuild-progress { margin-left: auto; }
.rebuild-failed { color: #d97706; }

.candidate-card { margin-bottom: 12px; }
.candidate-title { display:flex; gap:8px; align-items:center; color:#334155; }
.candidate-meta { display:flex; gap:10px; align-items:center; margin-top:8px; font-size:12px; color:#64748b; }
.candidate-card p { margin:10px 0 6px; font-size:13px; color:#475569; }
.candidate-evidence { padding:8px; border-radius:6px; background:#f8fafc; font-size:12px; line-height:1.6; color:#64748b; }
.candidate-source { margin-top:6px; font-size:12px; color:#94a3b8; }
.candidate-actions { display:flex; gap:8px; margin-top:10px; }

.kg-body {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
  overflow: hidden;
}

.graph-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  gap: 8px;
  overflow: hidden;
}

.graph-container {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  border: none;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
  overflow: hidden;
  min-height: 0;
}
.graph-container :deep(.el-card__body) {
  flex: 1;
  padding: 0;
  position: relative;
  overflow: hidden;
  background: #f8fafc;
}

.graph-canvas {
  width: 100%;
  height: 100%;
}

.graph-hint {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  color: #94a3b8;
  pointer-events: none;
  z-index: 1;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(4px);
  padding: 4px 14px;
  border-radius: 20px;
  white-space: nowrap;
  border: 1px solid rgba(203,213,225,0.3);
}

/* ── Legend ── */
.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 20px;
  padding: 10px 18px;
  background: #fff;
  border: none;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  flex-shrink: 0;
  align-items: center;
}
.legend-title {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  margin-right: 2px;
  letter-spacing: 0.3px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-label {
  font-size: 12px;
  color: #64748b;
}

/* ── Detail Panel ── */
.detail-panel {
  width: 240px;
  flex-shrink: 0;
  border: none;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
}
.detail-panel :deep(.el-card__header) {
  background: transparent;
  border-bottom: 1px solid #f1f5f9;
  font-weight: 600;
  color: #334155;
  font-size: 14px;
  padding: 14px 18px;
}
.detail-name {
  font-size: 17px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 2px solid #f1f5f9;
}
.detail-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}
.detail-key {
  color: #94a3b8;
  flex-shrink: 0;
  width: 32px;
  font-weight: 500;
}
.detail-val { color: #334155; }
.detail-rels {
  margin-top: 14px;
  border-top: 1px solid #f1f5f9;
  padding-top: 12px;
}
.detail-rels-title {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 8px;
}
.detail-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  gap: 8px;
}

.stat-item {
  text-align: center;
  padding: 14px 0;
}
.stat-item + .stat-item { border-top: 1px solid #f1f5f9; }
.stat-num {
  display: block;
  font-size: 30px;
  font-weight: 700;
  color: #334155;
  line-height: 1.2;
}
.stat-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}

.rel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  font-size: 12px;
  border-radius: 6px;
  margin-bottom: 4px;
  background: #f8fafc;
  transition: background 0.15s;
}
.rel-item:hover { background: #f1f5f9; }
.rel-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.rel-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #334155;
  font-weight: 500;
}
.rel-type {
  font-size: 10px;
  color: #64748b;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.kg-page :deep(.el-card) { border-radius: 10px; }
.kg-page :deep(.vis-network:focus) { outline: none; }
.kg-page :deep(.vis-network),
.kg-page :deep(.vis-network canvas) {
  background: transparent !important;
}
.kg-page :deep(.vis-tooltip) {
  background: #fff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 8px !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.08) !important;
  padding: 6px 10px !important;
  font-family: 'PingFang SC','Microsoft YaHei',sans-serif !important;
}
</style>
