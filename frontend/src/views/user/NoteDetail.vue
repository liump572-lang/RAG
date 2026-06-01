<template>
  <div class="detail-page" v-loading="loading">
    <div class="detail-header-bar">
      <el-button @click="$router.back()" text>← 返回</el-button>
      <div class="detail-header-actions">
        <span v-if="lastRefreshed" class="refresh-time">最近刷新：{{ formatTime(lastRefreshed) }}</span>
        <button class="btn btn-secondary btn-sm" @click="refresh" :disabled="isRefreshing">
          {{ isRefreshing ? '刷新中...' : '🔄 刷新' }}
        </button>
      </div>
    </div>
    <el-card v-if="note">
      <div class="detail-header">
        <div style="display:flex;align-items:center;gap:8px">
          <h2>{{ note.title }}</h2>
          <el-tag v-if="note.status === 'pending'" size="small" type="warning">审核中</el-tag>
          <el-tag v-if="note.status === 'rejected'" size="small" type="danger">未通过</el-tag>
          <el-tag v-if="note.status === 'published'" size="small" type="success">已通过</el-tag>
          <el-tag v-if="note.is_pinned" size="small" type="warning">置顶</el-tag>
        </div>
        <div class="detail-meta">
          <span>作者：{{ note.username }}</span>
          <span>时间：{{ note.created_at?.slice(0, 10) }}</span>
        </div>
        <el-alert v-if="note.status === 'rejected' && note.reject_reason" title="未通过原因" :description="note.reject_reason" type="error" show-icon :closable="false" style="margin-top:8px" />
      </div>
      <div class="detail-content" style="white-space:pre-wrap;line-height:1.8">{{ note.content }}</div>
      <div v-if="note.tags?.length" class="detail-tags">
        <el-tag v-for="t in note.tags" :key="t" size="small">{{ t }}</el-tag>
      </div>
      <div class="detail-actions">
        <el-button :type="liked ? 'primary' : 'default'" @click="handleLike">
          👍 {{ note.like_count }}
        </el-button>
        <el-button :type="favorited ? 'warning' : 'default'" @click="handleFavorite">
          ⭐ {{ note.favorite_count }}
        </el-button>
        <el-button v-if="note.user_id === auth.user?.id" @click="$router.push(`/user/notes/publish/${note.id}`)">编辑</el-button>
      </div>
    </el-card>

    <el-card style="margin-top:16px">
      <template #header>评论 ({{ comments.length }})</template>
      <div class="comment-input">
        <el-input v-model="commentText" placeholder="写下你的评论..." @keyup.enter="handleComment" />
        <el-button type="primary" @click="handleComment" style="margin-top:8px">发表</el-button>
      </div>
      <div v-for="c in comments" :key="c.id" class="comment-item">
        <strong>{{ c.username }}</strong>
        <span class="comment-time">{{ c.created_at?.slice(0, 16) }}</span>
        <p>{{ c.content }}</p>
      </div>
      <el-empty v-if="!comments.length" description="暂无评论" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, onBeforeRouteUpdate } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getNote, toggleLike, toggleFavorite, getComments, addComment } from '@/api/notes'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

const route = useRoute()
const auth = useAuthStore()
const note = ref(null)
const comments = ref([])
const loading = ref(false)
const liked = ref(false)
const favorited = ref(false)
const commentText = ref('')

async function loadNote(noteId) {
  loading.value = true
  try {
    const [noteRes, commentRes] = await Promise.all([
      getNote(noteId),
      getComments(noteId),
    ])
    if (noteRes.code === 200) note.value = noteRes.data
    if (commentRes.code === 200) comments.value = commentRes.data
  } finally {
    loading.value = false
  }
}

onMounted(() => loadNote(route.params.id))

onBeforeRouteUpdate((to) => {
  if (to.params.id !== route.params.id) {
    loadNote(to.params.id)
  }
})

async function fetchLatest() {
  const noteId = route.params.id
  if (!noteId) return
  const res = await getNote(noteId)
  if (res.code === 200) note.value = res.data
  const commentRes = await getComments(noteId)
  if (commentRes.code === 200) comments.value = commentRes.data
}

const { lastRefreshed, isRefreshing, refresh } = useAutoRefresh(fetchLatest, 15000)

function formatTime(d) {
  if (!d) return ''
  const now = new Date()
  const diff = now - d
  if (diff < 10000) return '刚刚'
  if (diff < 60000) return Math.floor(diff / 1000) + ' 秒前'
  return Math.floor(diff / 60000) + ' 分钟前'
}

async function handleLike() {
  const res = await toggleLike(note.value.id)
  if (res.code === 200) {
    liked.value = !liked.value
    note.value.like_count = res.data.count
  }
}

async function handleFavorite() {
  const res = await toggleFavorite(note.value.id)
  if (res.code === 200) {
    favorited.value = !favorited.value
    note.value.favorite_count = res.data.count
  }
}

async function handleComment() {
  const text = commentText.value.trim()
  if (!text) return
  const res = await addComment(note.value.id, { content: text })
  if (res.code === 200) {
    comments.value.push(res.data)
    commentText.value = ''
    note.value.comment_count++
    ElMessage.success('评论成功')
  }
}
</script>

<style scoped>
.detail-header { margin-bottom: 16px; }
.detail-header h2 { margin: 0 0 8px 0; }
.detail-meta { display: flex; gap: 16px; font-size: 13px; color: #909399; align-items: center; }
.detail-content { padding: 16px 0; }
.detail-tags { display: flex; gap: 6px; margin-bottom: 12px; }
.detail-actions { display: flex; gap: 8px; }
.comment-input { margin-bottom: 16px; }
.comment-item { padding: 12px 0; border-bottom: 1px solid #f0f0f0; }
.comment-item p { margin: 4px 0 0; font-size: 14px; }
.comment-time { font-size: 12px; color: #909399; margin-left: 8px; }
.detail-header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.detail-header-actions { display: flex; align-items: center; gap: 8px; }
.refresh-time { font-size: 12px; color: var(--text3); }
</style>
