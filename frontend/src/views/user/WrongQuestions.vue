<template>
  <div class="wrong-q-page">
    <div class="page-toolbar">
      <h2>错题本</h2>
      <div>
        <el-button type="primary" @click="startPractice">随机练习</el-button>
        <el-button @click="showAdd = true">手动录入</el-button>
      </div>
    </div>

    <el-row :gutter="12" class="stats-row">
      <el-col :span="6"><el-card><div class="stat-card"><span class="stat-num">{{ stats.total }}</span><span>总计</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat-card"><span class="stat-num pending">{{ statusCount('pending') }}</span><span>待复习</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat-card"><span class="stat-num unmastered">{{ statusCount('unmastered') }}</span><span>未掌握</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat-card"><span class="stat-num mastered">{{ statusCount('mastered') }}</span><span>已掌握</span></div></el-card></el-col>
    </el-row>

    <el-card style="margin-top:16px">
      <el-form :model="filter" inline>
        <el-form-item>
          <el-input v-model="filter.keyword" placeholder="搜索题目" clearable style="width:180px" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="filter.subject_id" placeholder="科目" clearable style="width:130px" @change="fetchList">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="filter.mastery_status" placeholder="掌握状态" clearable style="width:130px" @change="fetchList">
            <el-option label="待复习" value="pending" />
            <el-option label="未掌握" value="unmastered" />
            <el-option label="已掌握" value="mastered" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="filter.error_reason" placeholder="错误原因" clearable style="width:130px" @change="fetchList">
            <el-option label="知识漏洞" value="knowledge_gap" />
            <el-option label="理解偏差" value="misunderstanding" />
            <el-option label="粗心大意" value="careless" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchList">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="list" v-loading="loading" @expand-change="handleExpand" row-key="id">
        <el-table-column type="expand" width="30">
          <template #default="{ row }">
            <div style="padding:12px">
              <p><strong>问题：</strong>{{ row.question_content }}</p>
              <p><strong>正确答案：</strong>{{ row.correct_answer || '—' }}</p>
              <p><strong>我的答案：</strong>{{ row.user_answer || '—' }}</p>
              <p><strong>掌握状态：</strong>{{ statusLabel(row.mastery_status) }}</p>
              <p><strong>复习次数：</strong>{{ row.review_count }}</p>
              <div style="margin-top:8px">
                <el-button size="small" type="primary" @click.stop="editRow(row)">编辑</el-button>
                <el-button size="small" type="danger" @click.stop="handleDelete(row)">删除</el-button>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="question_content" label="题目" min-width="300" show-overflow-tooltip />
        <el-table-column label="难度" width="80">
          <template #default="{ row }">
            <el-rate :model-value="row.difficulty" disabled size="small" />
          </template>
        </el-table-column>
        <el-table-column label="错误原因" width="110">
          <template #default="{ row }">{{ reasonLabel(row.error_reason) }}</template>
        </el-table-column>
        <el-table-column label="掌握状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.mastery_status)" size="small">{{ statusLabel(row.mastery_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_count" label="复习" width="60" />
        <el-table-column prop="created_at" label="添加时间" width="170" />
      </el-table>

      <div class="pagination-wrap">
        <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next" @current-change="fetchList" />
      </div>
    </el-card>

    <el-dialog v-model="showAdd" title="录入错题" width="600px">
      <el-form :model="addForm" :rules="addRules" label-width="80px" ref="addFormRef">
        <el-form-item label="科目" prop="subject_id">
          <el-select v-model="addForm.subject_id" style="width:100%">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="题目" prop="question_content">
          <el-input v-model="addForm.question_content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="正确答案">
          <el-input v-model="addForm.correct_answer" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="我的答案">
          <el-input v-model="addForm.user_answer" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="错误原因">
          <el-select v-model="addForm.error_reason" style="width:100%">
            <el-option label="知识漏洞" value="knowledge_gap" />
            <el-option label="理解偏差" value="misunderstanding" />
            <el-option label="粗心大意" value="careless" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-rate v-model="addForm.difficulty" :max="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleAdd">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" title="编辑错题" width="600px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="题目">
          <el-input v-model="editForm.question_content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="正确答案">
          <el-input v-model="editForm.correct_answer" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="我的答案">
          <el-input v-model="editForm.user_answer" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="错误原因">
          <el-select v-model="editForm.error_reason" style="width:100%">
            <el-option label="知识漏洞" value="knowledge_gap" />
            <el-option label="理解偏差" value="misunderstanding" />
            <el-option label="粗心大意" value="careless" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-rate v-model="editForm.difficulty" :max="5" />
        </el-form-item>
        <el-form-item label="掌握状态">
          <el-select v-model="editForm.mastery_status" style="width:100%">
            <el-option label="待复习" value="pending" />
            <el-option label="未掌握" value="unmastered" />
            <el-option label="已掌握" value="mastered" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPractice" title="错题练习" width="700px" :close-on-click-modal="false">
      <div v-if="practiceSet.length">
        <div class="practice-progress">第 {{ practiceIdx + 1 }} / {{ practiceSet.length }} 题</div>
        <el-card v-if="currentPractice">
          <p class="practice-question"><strong>题目：</strong>{{ currentPractice.question_content }}</p>
          <p v-if="revealed"><strong>正确答案：</strong>{{ currentPractice.correct_answer || '—' }}</p>
          <p v-if="revealed"><strong>你的答案：</strong>{{ currentPractice.user_answer || '—' }}</p>
          <p v-if="revealed"><strong>错误原因：</strong>{{ reasonLabel(currentPractice.error_reason) }}</p>
          <div style="margin-top:16px;text-align:center">
            <el-button v-if="!revealed" type="primary" @click="revealed = true">查看答案</el-button>
            <template v-else>
              <el-button type="success" @click="handlePracticeResult(true)">回答正确</el-button>
              <el-button type="danger" @click="handlePracticeResult(false)">回答错误</el-button>
            </template>
          </div>
        </el-card>
      </div>
      <div v-else style="text-align:center;padding:40px">暂无符合条件的错题</div>
      <template #footer>
        <el-button @click="showPractice = false">退出练习</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getWrongQuestions, getWrongStats, createWrongQuestion,
  updateWrongQuestion, deleteWrongQuestion, getPracticeSet, reviewWrongQuestion,
} from '@/api/wrongQuestions'
import { getSubjects } from '@/api/subjects'

const subjects = ref([])
const list = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const saving = ref(false)
const stats = ref({ total: 0, by_status: [] })
const showAdd = ref(false)
const showEdit = ref(false)
const editTarget = ref(null)
const showPractice = ref(false)
const practiceSet = ref([])
const practiceIdx = ref(0)
const revealed = ref(false)
const addFormRef = ref(null)

const filter = reactive({ keyword: '', subject_id: null, mastery_status: null, error_reason: null })
const addForm = reactive({ subject_id: null, question_content: '', correct_answer: '', user_answer: '', error_reason: null, difficulty: 3 })
const editForm = reactive({ question_content: '', correct_answer: '', user_answer: '', error_reason: null, difficulty: 3, mastery_status: null })
const addRules = {
  subject_id: [{ required: true, message: '请选择科目', trigger: 'change' }],
  question_content: [{ required: true, message: '请输入题目', trigger: 'blur' }],
}

const currentPractice = computed(() => practiceSet.value[practiceIdx.value] || null)

onMounted(async () => {
  const res = await getSubjects()
  if (res.code === 200) subjects.value = res.data
  fetchList()
  fetchStats()
})

function statusLabel(s) {
  return s === 'pending' ? '待复习' : s === 'mastered' ? '已掌握' : '未掌握'
}
function statusTag(s) {
  return s === 'pending' ? 'warning' : s === 'mastered' ? 'success' : 'danger'
}
function reasonLabel(r) {
  return r === 'knowledge_gap' ? '知识漏洞' : r === 'misunderstanding' ? '理解偏差' : r === 'careless' ? '粗心大意' : r === 'other' ? '其他' : '—'
}
function statusCount(s) {
  const found = stats.value.by_status.find(x => x.status === s)
  return found ? found.count : 0
}

async function fetchList() {
  loading.value = true
  try {
    const params = { page: page.value, size: 20 }
    if (filter.keyword) params.keyword = filter.keyword
    if (filter.subject_id) params.subject_id = filter.subject_id
    if (filter.mastery_status) params.mastery_status = filter.mastery_status
    if (filter.error_reason) params.error_reason = filter.error_reason
    const res = await getWrongQuestions(params)
    if (res.code === 200) {
      list.value = res.data.items
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  const res = await getWrongStats()
  if (res.code === 200) stats.value = res.data
}

function handleExpand(row, expandedRows) {}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除该错题吗？')
    await deleteWrongQuestion(row.id)
    ElMessage.success('已删除')
    fetchList()
    fetchStats()
  } catch {}
}

function editRow(row) {
  editTarget.value = row
  editForm.question_content = row.question_content
  editForm.correct_answer = row.correct_answer
  editForm.user_answer = row.user_answer
  editForm.error_reason = row.error_reason
  editForm.difficulty = row.difficulty
  editForm.mastery_status = row.mastery_status
  showEdit.value = true
}

async function handleAdd() {
  const valid = await addFormRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await createWrongQuestion(addForm)
    ElMessage.success('已添加')
    showAdd.value = false
    addForm.subject_id = null; addForm.question_content = ''; addForm.correct_answer = ''
    addForm.user_answer = ''; addForm.error_reason = null; addForm.difficulty = 3
    fetchList()
    fetchStats()
  } finally {
    saving.value = false
  }
}

async function handleEdit() {
  saving.value = true
  try {
    await updateWrongQuestion(editTarget.value.id, editForm)
    ElMessage.success('已更新')
    showEdit.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

async function startPractice() {
  const res = await getPracticeSet({ count: 10 })
  if (res.code === 200 && res.data.length) {
    practiceSet.value = res.data
    practiceIdx.value = 0
    revealed.value = false
    showPractice.value = true
  } else {
    ElMessage.info('暂无错题可练习')
  }
}

async function handlePracticeResult(isCorrect) {
  const item = currentPractice.value
  if (!item) return
  await reviewWrongQuestion(item.id, { is_correct: isCorrect })
  if (practiceIdx.value < practiceSet.value.length - 1) {
    practiceIdx.value++
    revealed.value = false
  } else {
    ElMessage.success('练习完成！')
    showPractice.value = false
    fetchList()
    fetchStats()
  }
}
</script>

<style scoped>
.wrong-q-page { padding: 0; }
.page-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-toolbar h2 { margin: 0; }
.stats-row :deep(.el-card__body) { padding: 12px; }
.stat-card { display: flex; flex-direction: column; align-items: center; }
.stat-num { font-size: 28px; font-weight: 700; }
.stat-num.pending { color: #e6a23c; }
.stat-num.unmastered { color: #f56c6c; }
.stat-num.mastered { color: #67c23a; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: center; }
.practice-progress { text-align: center; margin-bottom: 12px; font-size: 14px; color: #909399; }
.practice-question { font-size: 15px; line-height: 1.6; }
</style>
