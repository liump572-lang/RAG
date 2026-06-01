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
          <el-input v-model="filter.keyword" placeholder="搜索知识点" clearable style="width:180px" @keyup.enter="handleSearch" @clear="handleClearSearch" />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchGraph">刷新图谱</el-button>
          <el-button @click="fitGraph" :disabled="!network">自适应缩放</el-button>
          <el-button type="primary" @click="showAddNode">添加节点</el-button>
          <el-button type="success" @click="showAddEdge">添加关系</el-button>
          <el-button type="warning" @click="showGenerateDoc">生成文档</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="kg-body">
      <div class="graph-wrapper">
        <el-card class="graph-container" v-loading="loading">
          <div ref="graphRef" class="graph-canvas"></div>
          <el-empty v-if="!loading && graphData.nodes.length === 0" description="暂无图谱数据，请先导入种子数据" />
        </el-card>
        <div class="graph-legend">
          <div class="legend-title">关系类型</div>
          <div v-for="(cfg, type) in edgeTypeConfig" :key="type" class="legend-item">
            <span class="legend-line" :style="{ background: cfg.color, borderTop: '2px ' + cfg.dashes + ' ' + cfg.color }"></span>
            <span class="legend-label">{{ type }}</span>
          </div>
        </div>
      </div>
      <el-card class="detail-panel">
        <template #header>
          <span>{{ selectedNode ? '节点详情' : '图谱信息' }}</span>
        </template>
        <div v-if="selectedNode">
          <p><strong>名称：</strong>{{ selectedNode.label }}</p>
          <p><strong>ID：</strong>{{ selectedNode.id }}</p>
          <p><strong>科目：</strong>{{ selectedNode.group }}</p>
          <div v-if="nodeRelations.length" style="margin-top:10px;border-top:1px solid #eee;padding-top:10px">
            <p style="font-weight:600;margin-bottom:6px;">关联节点</p>
            <div v-for="rel in nodeRelations" :key="rel.id" class="rel-item">
              <span class="rel-dot" :style="{ background: edgeTypeConfig[rel.relation_type]?.color || '#999' }"></span>
              <span class="rel-text">{{ rel.target_name }}</span>
              <span class="rel-type">{{ rel.relation_type }}</span>
            </div>
          </div>
          <div style="margin-top:12px">
            <el-button size="small" @click="editNode(selectedNode)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeleteNode(selectedNode.id)">删除</el-button>
          </div>
        </div>
        <div v-else>
          <p>节点数：{{ graphData.nodes.length }}</p>
          <p>关系数：{{ graphData.edges.length }}</p>
          <p v-if="filter.keyword && highlightedNodes.size">匹配节点：{{ highlightedNodes.size }} 个</p>
          <p v-else>选择一个节点查看详情</p>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, onActivated, onDeactivated, nextTick } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { Network } from 'vis-network'
import 'vis-network/styles/vis-network.css'
import { getSubgraph, searchKnowledge, searchSubgraph, createPoint, updatePoint, deletePoint, createRelation, generateDocument } from '@/api/kg'
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
let network = null

const edgeTypeConfig = {
  PREREQUISITE: { color: '#e74c3c', dashes: 'dashed', label: '前置条件' },
  NEXT:         { color: '#2ecc71', dashes: 'solid', label: '后继' },
  RELATED:      { color: '#3498db', dashes: 'solid', label: '关联' },
  CONTAINS:     { color: '#9b59b6', dashes: 'dotted', label: '包含' },
  CONTRAST:     { color: '#f39c12', dashes: 'dashed', label: '对比' },
  EXAMINED_IN:  { color: '#e67e22', dashes: 'dotted', label: '考点' },
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
  if (!isSearchMode.value && graphData.value.nodes.length > 0) {
    fetchGraph(true)
  }
}, 30000)

onMounted(() => {
  fetchSubjects()
  fetchGraph()
  window.addEventListener('resize', handleResize)
})

onActivated(() => {
  if (graphData.value.nodes.length > 0) {
    autoRefresh()
  }
})

onDeactivated(() => {
  stopAutoRefresh()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (network) network.destroy()
})

function handleResize() {
  if (network && graphRef.value) {
    network.fit({ animation: false })
  }
}

async function fetchSubjects() {
  const res = await getSubjects()
  if (res.code === 200) {
    subjects.value = res.data.map(s => ({ id: s.id, name: s.name }))
  } else {
    ElNotification.error({ title: '获取科目列表失败', message: res.message || '未知错误' })
  }
}

async function fetchGraph(silent = false) {
  if (!silent) loading.value = true
  nodeRelations.value = []
  try {
    const params = {}
    if (filter.value.subject_id) params.subject_id = filter.value.subject_id

    const keyword = filter.value.keyword
    if (keyword) {
      isSearchMode.value = true
      const res = await searchSubgraph({ keyword, ...params })
      if (res.code === 200) {
        graphData.value = res.data
        try {
          const searchRes = await searchKnowledge({ keyword, subject_id: filter.value.subject_id || undefined })
          if (searchRes.code === 200) {
            highlightedNodes.value = new Set((searchRes.data || []).map(n => n.id))
          }
        } catch {}
      }
    } else {
      isSearchMode.value = false
      highlightedNodes.value = new Set()
      const res = await getSubgraph(params)
      if (res.code === 200) {
        graphData.value = res.data
      }
    }
    await nextTick()
    renderGraph()
    await nextTick()
    if (!silent) fitGraph()
  } finally {
    if (!silent) loading.value = false
  }
}

function getGroupColor(group) {
  const palette = [
    { background: 'rgba(64,158,255,0.15)', border: 'rgba(64,158,255,0.4)', highlight: 'rgba(64,158,255,0.25)' },
    { background: 'rgba(103,194,58,0.15)', border: 'rgba(103,194,58,0.4)', highlight: 'rgba(103,194,58,0.25)' },
    { background: 'rgba(230,162,60,0.15)', border: 'rgba(230,162,60,0.4)', highlight: 'rgba(230,162,60,0.25)' },
    { background: 'rgba(245,108,108,0.15)', border: 'rgba(245,108,108,0.4)', highlight: 'rgba(245,108,108,0.25)' },
    { background: 'rgba(144,147,153,0.15)', border: 'rgba(144,147,153,0.4)', highlight: 'rgba(144,147,153,0.25)' },
    { background: 'rgba(179,127,235,0.15)', border: 'rgba(179,127,235,0.4)', highlight: 'rgba(179,127,235,0.25)' },
    { background: 'rgba(54,207,201,0.15)', border: 'rgba(54,207,201,0.4)', highlight: 'rgba(54,207,201,0.25)' },
    { background: 'rgba(255,133,192,0.15)', border: 'rgba(255,133,192,0.4)', highlight: 'rgba(255,133,192,0.25)' },
  ]
  return palette[parseInt(group) % palette.length] || palette[0]
}

function getEdgeStyle(type) {
  const cfg = edgeTypeConfig[type] || { color: 'rgba(150,150,150,0.25)', dashes: 'solid' }
  return {
    color: cfg.color,
    dashes: cfg.dashes === 'dashed' ? [8, 4] : cfg.dashes === 'dotted' ? [2, 4] : false,
    opacity: 0.35,
  }
}

function renderGraph() {
  if (!graphRef.value || !graphData.value.nodes.length) return

  const hl = highlightedNodes.value
  const nodes = graphData.value.nodes.map(n => {
    const isHl = hl.size && hl.has(n.id)
    const colors = getGroupColor(n.group || '0')
    return {
      id: n.id,
      label: n.label,
      group: n.group || '0',
      title: `<b>${n.label}</b><br/>ID: ${n.id}<br/>科目: ${n.group || '未知'}`,
      size: isHl ? 32 : 20,
      font: {
        size: isHl ? 15 : 13,
        color: '#1a1a2e',
        face: 'Arial, sans-serif',
        strokeWidth: 2,
        strokeColor: '#ffffff',
      },
      borderWidth: isHl ? 4 : 2,
      borderWidthSelected: 4,
      color: isHl
        ? {
            background: 'rgba(230,162,60,0.15)',
            border: 'rgba(230,162,60,0.5)',
            highlight: { background: 'rgba(230,162,60,0.25)', border: 'rgba(230,162,60,0.6)' },
            hover: { background: 'rgba(230,162,60,0.2)', border: 'rgba(230,162,60,0.5)' },
          }
        : {
            background: colors.background,
            border: colors.border,
            highlight: { background: colors.highlight, border: colors.border },
            hover: { background: colors.highlight, border: colors.border },
          },
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.05)',
        size: isHl ? 12 : 6,
        x: 1,
        y: 2,
      },
      shape: 'circle',
    }
  })

  const edges = graphData.value.edges.map(e => {
    const style = getEdgeStyle(e.label)
    return {
      from: e.from,
      to: e.to,
      label: e.label,
      title: e.title || e.label,
      arrows: { to: { enabled: true, scaleFactor: 0.7, type: 'arrow' } },
      font: {
        size: 9,
        color: '#888',
        face: 'Arial, sans-serif',
        align: 'middle',
        strokeWidth: 2,
        strokeColor: '#ffffff',
      },
      smooth: { type: 'curvedCW', roundness: 0.12 },
      color: { color: style.color, highlight: style.color, hover: style.color, opacity: style.opacity },
      width: 1,
      dashes: style.dashes,
      selectionWidth: 2,
      hoverWidth: 2,
    }
  })

  const container = graphRef.value
  const options = {
    physics: {
      stabilization: { iterations: 300, updateInterval: 20 },
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -400,
        centralGravity: 0.0015,
        springLength: 320,
        springConstant: 0.008,
        damping: 0.6,
        avoidOverlap: 2,
      },
      maxVelocity: 25,
      minVelocity: 0.5,
      timestep: 0.35,
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      selectConnectedEdges: false,
      multiselect: false,
      navigationButtons: true,
      keyboard: true,
    },
    layout: {
      improvedLayout: true,
      randomSeed: 42,
    },
    edges: {
      color: 'rgba(150,150,150,0.12)',
      width: 1,
      smooth: { type: 'continuous' },
    },
    groups: {
      '0': { shape: 'circle', size: 20 },
      '1': { shape: 'circle', size: 20 },
      '2': { shape: 'circle', size: 20 },
      '3': { shape: 'circle', size: 20 },
      '4': { shape: 'circle', size: 20 },
      '5': { shape: 'circle', size: 20 },
      '6': { shape: 'circle', size: 20 },
      '7': { shape: 'circle', size: 20 },
    },
    nodes: {
      shape: 'circle',
      size: 20,
      font: { size: 13, color: '#1a1a2e', face: 'Arial, sans-serif', strokeWidth: 2, strokeColor: '#ffffff' },
      borderWidth: 2,
      shadow: { enabled: true, color: 'rgba(0,0,0,0.05)', size: 6, x: 1, y: 2 },
    },
  }

  if (network) {
    network.destroy()
    network = null
  }
  network = new Network(container, { nodes, edges }, options)

  network.on('click', (params) => {
    if (params.nodes.length) {
      const nodeId = params.nodes[0]
      const node = graphData.value.nodes.find(n => n.id === nodeId)
      selectedNode.value = node || null
      if (node) {
        const rels = []
        for (const e of graphData.value.edges) {
          if (String(e.from) === String(nodeId)) {
            const target = graphData.value.nodes.find(n => String(n.id) === String(e.to))
            if (target) rels.push({ id: nodeId + '-' + e.to, target_name: target.label, relation_type: e.label })
          }
          if (String(e.to) === String(nodeId)) {
            const source = graphData.value.nodes.find(n => String(n.id) === String(e.from))
            if (source) rels.push({ id: e.from + '-' + nodeId, target_name: source.label, relation_type: e.label })
          }
        }
        nodeRelations.value = rels
      } else {
        nodeRelations.value = []
      }
    } else {
      selectedNode.value = null
      nodeRelations.value = []
    }
  })

  network.on('doubleClick', () => {
    fitGraph()
  })

  network.on('stabilizationProgress', (params) => {
    if (params.iterations < 50) return
  })
}

function fitGraph() {
  if (!network) return
  if (isSearchMode.value && highlightedNodes.value.size) {
    const ids = Array.from(highlightedNodes.value).map(id => typeof id === 'number' ? id : id)
    network.fit({
      animation: { duration: 500, easingFunction: 'easeInOutQuad' },
      nodes: ids,
    })
  } else {
    network.fit({
      animation: { duration: 300, easingFunction: 'easeInOutQuad' },
    })
  }
}

async function handleSearch() {
  if (filter.value.keyword) {
    fetchGraph()
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
  nodeForm.value = { name: '', subject_id: null, difficulty: 3, description: '' }
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
}
.kg-toolbar .el-form {
  margin-bottom: 0;
}
.kg-body {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
}
.graph-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.graph-container {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
}
.graph-container :deep(.el-card__body) {
  flex: 1;
  padding: 10px;
  position: relative;
  overflow: hidden;
}
.graph-canvas {
  width: 100%;
  height: 100%;
  min-height: 400px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  background:
    linear-gradient(135deg, #f8f9fc 0%, #eef1f7 100%);
}
.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.85);
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  margin-top: 6px;
  flex-shrink: 0;
  align-items: center;
}
.legend-title {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-right: 4px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.legend-line {
  width: 20px;
  height: 0;
  border-top-width: 2px;
  border-top-style: solid;
  flex-shrink: 0;
}
.legend-label {
  font-size: 11px;
  color: #888;
}
.detail-panel {
  width: 240px;
  flex-shrink: 0;
}
.detail-panel p {
  margin: 4px 0;
  font-size: 13px;
}
.rel-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  font-size: 12px;
  border-radius: 4px;
  margin-bottom: 3px;
  background: rgba(0,0,0,0.02);
}
.rel-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.rel-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #333;
}
.rel-type {
  font-size: 10px;
  color: #999;
  background: rgba(0,0,0,0.04);
  padding: 1px 5px;
  border-radius: 3px;
}
.kg-page :deep(.el-card) {
  border-radius: 8px;
}
.kg-page :deep(.vis-network:focus) {
  outline: none;
}
</style>
