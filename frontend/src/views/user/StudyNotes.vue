<template>
  <div>
    <div class="page-header">
      <h2>心得广场</h2>
      <div class="header-actions">
        <span v-if="lastRefreshed" class="refresh-time">最近刷新：{{ formatTime(lastRefreshed) }}</span>
        <button class="btn btn-secondary btn-sm" @click="refresh" :disabled="isRefreshing">
          {{ isRefreshing ? '刷新中...' : '🔄 刷新' }}
        </button>
        <button class="btn btn-primary" @click="$router.push('/user/notes/publish')">+ 发布心得</button>
      </div>
    </div>

    <div class="filter-bar">
      <input v-model="filter.keyword" placeholder="搜索心得..." @keyup.enter="fetchNotes">
      <select v-model="filter.subject_id" @change="fetchNotes">
        <option :value="null">全部科目</option>
        <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <button class="btn btn-secondary btn-sm" @click="fetchNotes">🔍 搜索</button>
    </div>

    <div class="card-grid" v-loading="loading">
      <div v-for="note in notes" :key="note.id" class="note-card" @click="$router.push(`/user/notes/${note.id}`)">
        <div class="title">{{ note.title }}</div>
        <div class="meta">
          <span>{{ subjectMap[note.subject_id] || note.subject_id }}</span>
          <span>{{ note.username }}</span>
        </div>
        <div class="excerpt">{{ note.content.slice(0, 150) }}{{ note.content.length > 150 ? '...' : '' }}</div>
        <div class="stats">
          <span>❤️ {{ note.like_count }}</span>
          <span>⭐ {{ note.favorite_count }}</span>
          <span>💬 {{ note.comment_count }}</span>
          <span style="margin-left:auto">{{ note.created_at?.slice(0, 10) }}</span>
        </div>
      </div>
    </div>
    <el-empty v-if="!notes.length && !loading" description="暂无已通过的心得" />
    <div class="pagination-wrap" v-if="total > 0">
      <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next" @current-change="fetchNotes" background />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { getNotes } from '@/api/notes'
import { getSubjects } from '@/api/subjects'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

const notes = ref([])
const subjects = ref([])
const subjectMap = ref({})
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filter = reactive({ keyword: '', subject_id: null })

onMounted(async () => {
  const res = await getSubjects()
  if (res.code === 200) {
    subjects.value = res.data
    res.data.forEach(s => subjectMap.value[s.id] = s.name)
  }
  await fetchNotes()
})

async function refreshAll() {
  await fetchNotes()
}

const { lastRefreshed, isRefreshing, refresh } = useAutoRefresh(refreshAll)

function formatTime(d) {
  if (!d) return ''
  const now = new Date()
  const diff = now - d
  if (diff < 10000) return '刚刚'
  if (diff < 60000) return Math.floor(diff / 1000) + ' 秒前'
  return Math.floor(diff / 60000) + ' 分钟前'
}

async function fetchNotes() {
  loading.value = true
  try {
    const params = { page: page.value, size: 20 }
    if (filter.keyword) params.keyword = filter.keyword
    if (filter.subject_id) params.subject_id = filter.subject_id
    const res = await getNotes(params)
    if (res.code === 200) {
      notes.value = res.data.items.filter(n => n.status === 'published')
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; align-items: center; gap: 8px; }
.refresh-time { font-size: 12px; color: var(--text3); }
</style>
