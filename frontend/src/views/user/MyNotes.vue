<template>
  <div>
    <div class="page-header">
      <div class="header-left">
        <h2>我的心得</h2>
        <span class="header-subtitle">管理你发布的所有学习心得</span>
      </div>
      <div class="header-actions">
        <span v-if="lastRefreshed" class="refresh-time">最近刷新：{{ formatTime(lastRefreshed) }}</span>
        <button class="btn btn-secondary btn-sm" @click="refresh" :disabled="isRefreshing">
          {{ isRefreshing ? '刷新中...' : '🔄 刷新' }}
        </button>
        <button class="btn btn-primary" @click="$router.push('/user/notes/publish')">+ 发布心得</button>
      </div>
    </div>

    <div class="status-summary">
      <div class="status-item pending" :class="{ active: filter.status === 'pending' }" @click="toggleStatusFilter('pending')">
        <span class="count">{{ statusCounts.pending }}</span>
        <span class="label">审核中</span>
        <span class="desc">等待管理员审核</span>
      </div>
      <div class="status-item approved" :class="{ active: filter.status === 'published' }" @click="toggleStatusFilter('published')">
        <span class="count">{{ statusCounts.published }}</span>
        <span class="label">已通过</span>
        <span class="desc">已公开发布</span>
      </div>
      <div class="status-item rejected" :class="{ active: filter.status === 'rejected' }" @click="toggleStatusFilter('rejected')">
        <span class="count">{{ statusCounts.rejected }}</span>
        <span class="label">未通过</span>
        <span class="desc">被驳回，可修改重提</span>
      </div>
    </div>

    <div class="filter-bar">
      <input v-model="filter.keyword" placeholder="搜索我的心得..." @keyup.enter="fetchNotes">
      <select v-model="filter.subject_id" @change="fetchNotes">
        <option :value="null">全部科目</option>
        <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <select v-model="filter.status" @change="handleStatusFilter">
        <option :value="null">全部状态</option>
        <option value="pending">审核中</option>
        <option value="published">已通过</option>
        <option value="rejected">未通过</option>
      </select>
      <button class="btn btn-secondary btn-sm" @click="fetchNotes">🔍 搜索</button>
    </div>

    <div class="card-grid" v-loading="loading">
      <div v-for="note in notes" :key="note.id" class="note-card" @click="$router.push(`/user/notes/${note.id}`)">
        <div class="title">
          {{ note.title }}
          <el-tag :type="statusTagType(note.status)" size="small" style="margin-left:8px">{{ statusLabel(note.status) }}</el-tag>
        </div>
        <div class="meta">
          <span>{{ subjectMap[note.subject_id] || note.subject_id }}</span>
          <span>{{ note.created_at?.slice(0, 10) }}</span>
        </div>
        <div class="excerpt">{{ note.content.slice(0, 150) }}{{ note.content.length > 150 ? '...' : '' }}</div>
        <div class="stats">
          <span v-if="note.status === 'rejected' && note.reject_reason" class="reject-reason">❌ 驳回原因：{{ note.reject_reason }}</span>
          <span v-else-if="note.status === 'pending'" class="pending-hint">⏳ 等待管理员审核</span>
          <span v-else-if="note.status === 'published'" class="published-hint">✅ 已通过审核</span>
          <span v-if="note.status === 'published'" style="margin-left:12px">❤️ {{ note.like_count }} ⭐ {{ note.favorite_count }} 💬 {{ note.comment_count }}</span>
          <span v-if="note.status === 'rejected'" style="margin-left:auto">
            <button class="btn btn-text" @click.stop="$router.push(`/user/notes/publish/${note.id}`)">✏️ 修改重提</button>
          </span>
        </div>
      </div>
    </div>
    <el-empty v-if="!notes.length && !loading" description="暂无心得，点击上方「+ 发布心得」开始分享你的学习心得吧" />
    <div class="pagination-wrap">
      <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next" @current-change="fetchNotes" background />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { getNotes, getMyCounts } from '@/api/notes'
import { getSubjects } from '@/api/subjects'
import { useAuthStore } from '@/stores/auth'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

const auth = useAuthStore()
const notes = ref([])
const subjects = ref([])
const subjectMap = ref({})
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const statusCounts = ref({ pending: 0, published: 0, rejected: 0 })
const filter = reactive({ keyword: '', subject_id: null, status: null })

onMounted(async () => {
  const res = await getSubjects()
  if (res.code === 200) {
    subjects.value = res.data
    res.data.forEach(s => subjectMap.value[s.id] = s.name)
  }
  await fetchNotes()
})

const { lastRefreshed, isRefreshing, refresh } = useAutoRefresh(refreshAll)

async function refreshAll() {
  await fetchNotes()
}

function formatTime(d) {
  if (!d) return ''
  const now = new Date()
  const diff = now - d
  if (diff < 10000) return '刚刚'
  if (diff < 60000) return Math.floor(diff / 1000) + ' 秒前'
  return Math.floor(diff / 60000) + ' 分钟前'
}

function toggleStatusFilter(s) {
  filter.status = filter.status === s ? null : s
  page.value = 1
  fetchNotes()
}

function handleStatusFilter() {
  page.value = 1
  fetchNotes()
}

function statusTagType(status) {
  if (status === 'published') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

function statusLabel(status) {
  if (status === 'published') return '已通过'
  if (status === 'rejected') return '未通过'
  return '审核中'
}

async function fetchNotes() {
  loading.value = true
  try {
    const params = { page: page.value, size: 20, user_id: auth.user?.id }
    if (filter.keyword) params.keyword = filter.keyword
    if (filter.subject_id) params.subject_id = filter.subject_id
    if (filter.status) params.status = filter.status
    const [notesRes, countsRes] = await Promise.all([
      getNotes(params),
      getMyCounts(),
    ])
    if (notesRes.code === 200) {
      notes.value = notesRes.data.items
      total.value = notesRes.data.total
    }
    if (countsRes.code === 200) {
      statusCounts.value = {
        pending: countsRes.data.pending ?? 0,
        published: countsRes.data.published ?? 0,
        rejected: countsRes.data.rejected ?? 0,
      }
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: baseline; gap: 12px; }
.header-subtitle { font-size: 13px; color: var(--text3); }
.header-actions { display: flex; align-items: center; gap: 8px; }
.refresh-time { font-size: 12px; color: var(--text3); }
.reject-reason { color: var(--danger); font-size: 12px; }
.pending-hint { color: #e6a23c; font-size: 12px; }
.published-hint { color: #67c23a; font-size: 12px; }
.btn-text { background: none; border: none; color: var(--primary); cursor: pointer; font-size: 12px; padding: 0; }
.btn-text:hover { text-decoration: underline; }

.status-summary { display: flex; gap: 12px; margin-bottom: 16px; }
.status-item { flex: 1; text-align: center; padding: 14px 8px; border-radius: 10px; cursor: pointer; transition: all 0.2s; border: 2px solid transparent; background: rgba(255,255,255,0.04); }
.status-item:hover { transform: translateY(-2px); }
.status-item.active { border-color: currentColor; }
.status-item.pending { color: #e6a23c; }
.status-item.pending.active { background: rgba(230,162,60,0.08); }
.status-item.approved { color: #67c23a; }
.status-item.approved.active { background: rgba(103,194,58,0.08); }
.status-item.rejected { color: #f56c6c; }
.status-item.rejected.active { background: rgba(245,108,108,0.08); }
.status-item .count { display: block; font-size: 28px; font-weight: 700; }
.status-item .label { display: block; font-size: 13px; margin-top: 4px; opacity: 0.85; }
.status-item .desc { display: block; font-size: 11px; margin-top: 2px; opacity: 0.6; }
</style>
