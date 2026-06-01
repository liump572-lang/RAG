<template>
  <div class="review-page">
    <el-card>
      <div class="page-header">
        <h2>心得审核</h2>
        <el-radio-group v-model="filterStatus" @change="fetchList">
          <el-radio-button value="pending">待审核</el-radio-button>
          <el-radio-button value="published">已通过</el-radio-button>
          <el-radio-button value="rejected">已驳回</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 批量操作栏 -->
      <div v-if="filterStatus === 'pending'" class="batch-bar">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <el-button type="primary" size="small" :loading="aiAllLoading" @click="handleAiReviewAll">
            🤖 一键AI审核
          </el-button>
          <span v-if="total > 0" class="batch-info">共 {{ total }} 篇待审核</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px" v-if="selectedIds.length > 0">
          <span class="batch-info">已选 {{ selectedIds.length }} 篇</span>
          <el-button type="success" size="small" :loading="batchLoading" @click="batchApprove">
            通过选中
          </el-button>
          <el-button type="danger" size="small" :loading="batchLoading" @click="showBatchReject">
            驳回选中
          </el-button>
          <el-button size="small" @click="clearSelection">取消选择</el-button>
        </div>
      </div>

      <el-table :data="list" v-loading="loading" style="width:100%"
        @selection-change="onSelectionChange" ref="tableRef">
        <el-table-column type="selection" width="45" v-if="filterStatus === 'pending'" />
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="username" label="作者" width="100" />
        <el-table-column prop="like_count" label="赞" width="60" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="操作" width="280" fixed="right" v-if="filterStatus === 'pending'">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="handleApprove(row)">通过</el-button>
            <el-button size="small" type="danger" @click="showReject(row)">驳回</el-button>
            <el-button size="small" type="primary" @click="handleAiReview(row)">AI审核</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next" @current-change="fetchList" />
      </div>
    </el-card>

    <!-- 驳回对话框 -->
    <el-dialog v-model="rejectDialog" title="驳回原因" width="400px">
      <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请输入驳回原因" />
      <template #footer>
        <el-button @click="rejectDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 批量驳回对话框 -->
    <el-dialog v-model="batchRejectDialog" title="批量驳回" width="400px">
      <p style="margin:0 0 12px;color:var(--text2);font-size:13px">
        将驳回 {{ selectedIds.length }} 篇心得，可填写统一驳回原因：
      </p>
      <el-input v-model="batchRejectReason" type="textarea" :rows="3" placeholder="请输入驳回原因（可选）" />
      <template #footer>
        <el-button @click="batchRejectDialog = false">取消</el-button>
        <el-button type="primary" :loading="batchLoading" @click="handleBatchReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- AI审核对话框 -->
    <el-dialog v-model="aiDialog" title="AI 审核建议" width="550px">
      <div v-if="aiResult" class="ai-result">
        <div class="ai-header">
          <el-tag :type="aiResult.suggested_action === 'approve' ? 'success' : 'danger'" size="large">
            {{ aiResult.suggested_action === 'approve' ? '建议通过' : '建议驳回' }}
          </el-tag>
          <span class="ai-confidence">置信度：{{ (aiResult.confidence * 100).toFixed(0) }}%</span>
          <span class="ai-score">质量评分：{{ aiResult.quality_score }}/10</span>
        </div>
        <div class="ai-summary">
          <strong>综合评价：</strong>{{ aiResult.summary }}
        </div>
        <div class="ai-reasons">
          <strong>理由：</strong>
          <ul>
            <li v-for="r in aiResult.reasons" :key="r">{{ r }}</li>
          </ul>
        </div>
      </div>
      <div v-else class="ai-loading">
        <el-skeleton :rows="4" animated />
      </div>
      <template #footer>
        <el-button @click="aiDialog = false">关闭</el-button>
        <el-button v-if="aiResult?.suggested_action === 'approve'" type="success" :loading="saving" @click="handleApprove(aiTarget)">采纳：通过</el-button>
        <el-button v-if="aiResult?.suggested_action === 'reject'" type="danger" :loading="saving" @click="rejectWithAiReason">采纳：驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getReviewList, reviewNote, batchReview, aiReviewAllPending, aiReview } from '@/api/notes'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

const list = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filterStatus = ref('pending')
const tableRef = ref(null)

// 一键AI审核
const aiAllLoading = ref(false)

// 批量操作
const selectedIds = ref([])
const batchLoading = ref(false)
const batchRejectDialog = ref(false)
const batchRejectReason = ref('')

// 单个驳回
const rejectDialog = ref(false)
const rejectReason = ref('')
const saving = ref(false)
const rejectTarget = ref(null)

// AI审核
const aiDialog = ref(false)
const aiResult = ref(null)
const aiTarget = ref(null)

onMounted(() => fetchList())

useAutoRefresh(fetchList)

function statusType(s) { return s === 'published' ? 'success' : s === 'rejected' ? 'danger' : 'warning' }
function statusLabel(s) { return s === 'published' ? '已通过' : s === 'rejected' ? '已驳回' : '待审核' }

function onSelectionChange(rows) {
  selectedIds.value = rows.map(r => r.id)
}

function clearSelection() {
  tableRef.value?.clearSelection()
}

async function fetchList() {
  loading.value = true
  clearSelection()
  try {
    const res = await getReviewList({ page: page.value, size: 20, status: filterStatus.value })
    if (res.code === 200) {
      list.value = res.data.items
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

// ── 单个审核 ──
async function handleApprove(row) {
  await reviewNote(row.id, { action: 'approve' })
  ElMessage.success('已通过')
  fetchList()
}

function showReject(row) {
  rejectTarget.value = row
  rejectReason.value = ''
  rejectDialog.value = true
}

async function handleReject() {
  saving.value = true
  try {
    await reviewNote(rejectTarget.value.id, { action: 'reject', reject_reason: rejectReason.value })
    ElMessage.success('已驳回')
    rejectDialog.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

// ── 一键AI审核 ──
async function handleAiReviewAll() {
  aiAllLoading.value = true
  try {
    const res = await aiReviewAllPending()
    if (res.code === 200) {
      ElMessage.success(res.message || 'AI审核完成')
      fetchList()
    } else {
      ElMessage.error(res.message || 'AI审核失败')
    }
  } catch {
    ElMessage.error('AI审核请求失败')
  } finally {
    aiAllLoading.value = false
  }
}

// ── 批量审核 ──
async function batchApprove() {
  batchLoading.value = true
  try {
    const res = await batchReview({ ids: selectedIds.value, action: 'approve' })
    ElMessage.success(`已通过 ${res.data.approved} 篇心得`)
    fetchList()
  } finally {
    batchLoading.value = false
  }
}

function showBatchReject() {
  batchRejectReason.value = ''
  batchRejectDialog.value = true
}

async function handleBatchReject() {
  batchLoading.value = true
  try {
    const res = await batchReview({ ids: selectedIds.value, action: 'reject', reject_reason: batchRejectReason.value })
    ElMessage.success(`已驳回 ${res.data.rejected} 篇心得`)
    batchRejectDialog.value = false
    fetchList()
  } finally {
    batchLoading.value = false
  }
}

// ── AI 审核 ──
async function handleAiReview(row) {
  aiTarget.value = row
  aiDialog.value = true
  aiResult.value = null
  try {
    const res = await aiReview(row.id)
    if (res.code === 200) {
      aiResult.value = res.data
    } else {
      ElMessage.error(res.message || 'AI审核失败')
      aiDialog.value = false
    }
  } catch {
    ElMessage.error('AI审核请求失败')
    aiDialog.value = false
  }
}

async function rejectWithAiReason() {
  if (!aiResult.value?.reasons?.length) return
  const reason = aiResult.value.reasons.slice(0, 2).join('；')
  saving.value = true
  try {
    await reviewNote(aiTarget.value.id, { action: 'reject', reject_reason: reason })
    ElMessage.success('已驳回')
    aiDialog.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }
.page-header h2 { margin:0; }
.pagination-wrap { margin-top:20px; display:flex; justify-content:center; }

.batch-bar {
  display:flex; align-items:center; gap:10px;
  padding:10px 14px; margin-bottom:12px;
  background:var(--el-color-primary-light-9, #f0f5ff);
  border-radius:8px; border:1px solid var(--el-color-primary-light-5, #d0d9ff);
}
.batch-info { font-size:13px; font-weight:600; color:var(--primary); margin-right:4px; }

.ai-result { font-size:14px; }
.ai-header { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
.ai-confidence { font-size:13px; color:#909399; }
.ai-score { font-size:13px; color:#e6a23c; }
.ai-summary { margin-bottom:12px; padding:12px; background:#f5f7fa; border-radius:6px; }
.ai-reasons ul { margin:4px 0 0; padding-left:20px; }
.ai-reasons li { margin:4px 0; }
.ai-loading { padding:20px; }
</style>
