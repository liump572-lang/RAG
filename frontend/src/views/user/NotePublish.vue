<template>
  <div class="publish-page">
    <el-card>
      <h2>{{ isEdit ? '编辑心得' : '发布心得' }}</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" :disabled="submittedNoteId && noteStatus === 'pending'">
        <el-form-item v-if="!isEdit" label="科目" prop="subject_id">
          <el-select v-model="form.subject_id" placeholder="请选择科目" style="width:100%">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" maxlength="255" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="12" maxlength="50000" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create default-first-option style="width:100%">
            <el-option v-for="t in commonTags" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!submittedNoteId || noteStatus !== 'pending'">
          <el-button type="primary" :loading="saving" @click="handleSave">{{ isEdit ? '保存修改' : '提交审核' }}</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>

      <!-- 提交后状态追踪卡片 -->
      <div v-if="submittedNoteId" class="status-tracker">
        <el-divider />
        <h3 style="margin-bottom:12px">📋 提交状态</h3>
        <el-alert
          :title="statusText"
          :type="statusType"
          :description="statusDescription"
          :closable="false"
          show-icon
        >
          <template v-if="noteStatus === 'rejected' && rejectReason" #default>
            <div style="margin-top:8px">
              <strong>驳回原因：</strong>{{ rejectReason }}
              <el-button type="primary" size="small" style="margin-left:12px" @click="handleEditAfterReject">修改后重新提交</el-button>
            </div>
          </template>
        </el-alert>
        <div style="margin-top:12px;font-size:13px;color:var(--text3)">
          状态自动刷新中... 最近刷新：{{ lastStatusRefresh || '刚刚' }}
          <el-button size="small" text @click="checkNoteStatus" :loading="statusChecking">手动刷新</el-button>
        </div>
        <div style="margin-top:12px;display:flex;gap:8px">
          <el-button size="small" @click="$router.push('/user/my-notes')">查看我的心得列表</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createNote, getNote, updateNote, getNoteStatus } from '@/api/notes'
import { getSubjects } from '@/api/subjects'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const saving = ref(false)
const isEdit = ref(false)
const subjects = ref([])

const submittedNoteId = ref(null)
const noteStatus = ref('')
const rejectReason = ref('')
const lastStatusRefresh = ref('')
const statusChecking = ref(false)
let statusTimer = null

const commonTags = ['计算机网络', '操作系统', '数据结构', '数据库', '计算机组成原理', '机器学习', '深度学习', '人工智能', '编程语言', '算法']

const form = reactive({
  subject_id: null, title: '', content: '', tags: [],
})

const rules = {
  subject_id: [{ required: true, message: '请选择科目', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }],
}

const statusType = computed(() => {
  if (noteStatus.value === 'published') return 'success'
  if (noteStatus.value === 'rejected') return 'error'
  return 'warning'
})

const statusText = computed(() => {
  if (noteStatus.value === 'published') return '审核已通过'
  if (noteStatus.value === 'rejected') return '审核未通过'
  return '审核中'
})

const statusDescription = computed(() => {
  if (noteStatus.value === 'published') return '你的心得已通过审核，现在其他用户可以看到它了。'
  if (noteStatus.value === 'rejected') return '你的心得未通过审核，请根据驳回原因修改后重新提交。'
  return '你的心得已提交，正在等待管理员审核，请耐心等待。'
})

onMounted(async () => {
  const res = await getSubjects()
  if (res.code === 200) subjects.value = res.data
  if (route.params.id) {
    isEdit.value = true
    const noteRes = await getNote(route.params.id)
    if (noteRes.code === 200) {
      form.subject_id = noteRes.data.subject_id
      form.title = noteRes.data.title
      form.content = noteRes.data.content
      form.tags = noteRes.data.tags || []
      if (noteRes.data.status === 'rejected' && noteRes.data.reject_reason) {
        ElMessage.warning('未通过原因：' + noteRes.data.reject_reason)
      }
    }
  }
})

onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer)
})

function startStatusPolling(noteId) {
  stopStatusPolling()
  checkNoteStatus(noteId)
  statusTimer = setInterval(() => checkNoteStatus(noteId), 10000)
}

function stopStatusPolling() {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
}

async function checkNoteStatus(noteIdOverride) {
  const id = noteIdOverride || submittedNoteId.value
  if (!id) return
  statusChecking.value = true
  try {
    const res = await getNoteStatus(id)
    if (res.code === 200) {
      const prev = noteStatus.value
      noteStatus.value = res.data.status
      rejectReason.value = res.data.reject_reason || ''
      if (res.data.updated_at) {
        lastStatusRefresh.value = new Date(res.data.updated_at).toLocaleTimeString('zh-CN')
      }
      // 状态变更提示
      if (prev && prev !== res.data.status) {
        if (res.data.status === 'published') {
          ElMessage.success('你的心得已通过审核！')
        } else if (res.data.status === 'rejected') {
          ElMessage.error('你的心得未通过审核')
        }
        stopStatusPolling()
      }
      // 终态停止轮询
      if (res.data.status === 'published' || res.data.status === 'rejected') {
        stopStatusPolling()
      }
    }
  } catch {
    // 静默处理
  } finally {
    statusChecking.value = false
  }
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value) {
      const res = await updateNote(route.params.id, { title: form.title, content: form.content, tags: form.tags })
      ElMessage.success('更新成功，已重新提交审核')
      if (res.code === 200 && res.data?.id) {
        submittedNoteId.value = res.data.id
        noteStatus.value = 'pending'
        rejectReason.value = ''
        startStatusPolling(res.data.id)
      }
    } else {
      const res = await createNote({ subject_id: form.subject_id, title: form.title, content: form.content, tags: form.tags })
      ElMessage.success('已提交审核')
      if (res.code === 200 && res.data?.id) {
        submittedNoteId.value = res.data.id
        noteStatus.value = 'pending'
        rejectReason.value = ''
        startStatusPolling(res.data.id)
      }
    }
  } finally {
    saving.value = false
  }
}

function handleEditAfterReject() {
  // 用户点击修改后，清空状态卡片，回到编辑模式
  submittedNoteId.value = null
  noteStatus.value = ''
  rejectReason.value = ''
  stopStatusPolling()
}
</script>

<style scoped>
.publish-page h2 { margin-top: 0; margin-bottom: 20px; }
.status-tracker { margin-top: 16px; }
</style>
