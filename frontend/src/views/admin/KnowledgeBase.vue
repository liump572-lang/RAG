<template>
  <div class="knowledge-base">
    <el-card>
      <div class="page-header">
        <h2>知识库管理</h2>
        <el-button type="primary" @click="showUpload">上传文档</el-button>
      </div>

      <el-form :model="filter" inline class="filter-bar">
        <el-form-item label="科目">
          <el-select v-model="filter.subject_id" placeholder="全部" clearable style="width:140px">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filter.doc_type" placeholder="全部" clearable style="width:120px">
            <el-option label="教材" value="textbook" />
            <el-option label="真题" value="exam" />
            <el-option label="笔记" value="note" />
            <el-option label="补充" value="supplement" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filter.parse_status" placeholder="全部" clearable style="width:120px">
            <el-option label="等待中" value="pending" />
            <el-option label="解析中" value="parsing" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-input v-model="filter.keyword" placeholder="搜索文档标题" clearable style="width:200px" @keyup.enter="fetchDocs" />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchDocs">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="documents" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="subject_name" label="科目" width="120" />
        <el-table-column prop="file_type" label="格式" width="70">
          <template #default="{ row }">
            <el-tag size="small">{{ row.file_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="doc_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="docTypeTag(row.doc_type)" size="small">{{ docTypeLabel(row.doc_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="parse_status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.parse_status)" size="small">{{ statusLabel(row.parse_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="片段数" width="70" />
        <el-table-column prop="created_at" label="上传时间" width="170" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewChunks(row)">片段</el-button>
            <el-button size="small" @click="handleReparse(row)">重新解析</el-button>
            <el-popconfirm title="确认删除该文档？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="size"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchDocs"
        />
      </div>
    </el-card>

    <el-dialog v-model="uploadVisible" title="上传文档" width="520px">
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="80px">
        <el-form-item label="科目" prop="subject_id">
          <div style="display:flex;gap:6px">
            <el-select v-model="uploadForm.subject_id" placeholder="请选择科目" style="flex:1">
              <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
            <el-button type="primary" :icon="Plus" @click="handleAddSubject" />
          </div>
        </el-form-item>
        <el-form-item label="标题" prop="title">
          <el-input v-model="uploadForm.title" />
        </el-form-item>
        <el-form-item label="类型" prop="doc_type">
          <el-select v-model="uploadForm.doc_type" style="width:100%">
            <el-option label="教材" value="textbook" />
            <el-option label="真题" value="exam" />
            <el-option label="笔记" value="note" />
            <el-option label="补充" value="supplement" />
          </el-select>
        </el-form-item>
        <el-form-item label="年份" prop="year" v-if="uploadForm.doc_type === 'exam'">
          <el-input-number v-model="uploadForm.year" :min="2000" :max="2030" />
        </el-form-item>
        <el-form-item label="题型" prop="question_type" v-if="uploadForm.doc_type === 'exam'">
          <el-input v-model="uploadForm.question_type" placeholder="如：选择题、填空题" />
        </el-form-item>
        <el-form-item label="文件" prop="file">
          <el-upload
            ref="fileUploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.docx,.pptx,.txt,.md"
            :on-change="onFileChange"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <span style="font-size:12px;color:#909399">支持 pdf/docx/pptx/txt/md</span>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="chunkVisible" title="文档片段" width="700px">
      <div v-loading="chunkLoading">
        <div v-for="c in chunks" :key="c.id" class="chunk-item">
          <div class="chunk-header">片段 #{{ c.chunk_index }} ({{ c.char_count }} 字符)</div>
          <div class="chunk-content">{{ c.content }}</div>
        </div>
        <el-empty v-if="!chunks.length" description="暂无片段" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getDocumentList, uploadDocument, deleteDocument, reparseDocument, getDocumentChunks } from '@/api/kb'
import { getSubjects, createSubject } from '@/api/subjects'

const documents = ref([])
const subjects = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const size = ref(20)

const filter = reactive({
  subject_id: null,
  doc_type: null,
  parse_status: null,
  keyword: '',
})

const uploadVisible = ref(false)
const uploading = ref(false)
const uploadFormRef = ref(null)
const selectedFile = ref(null)
const fileUploadRef = ref(null)

const uploadForm = reactive({
  subject_id: null,
  title: '',
  doc_type: 'textbook',
  year: null,
  question_type: '',
})

const uploadRules = {
  subject_id: [{ required: true, message: '请选择科目', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  doc_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

const chunkVisible = ref(false)
const chunks = ref([])
const chunkLoading = ref(false)

const docTypeMap = { textbook: '教材', exam: '真题', note: '笔记', supplement: '补充' }
const statusMap = { pending: '等待中', parsing: '解析中', success: '成功', failed: '失败' }

function docTypeLabel(v) { return docTypeMap[v] || v }
function docTypeTag(v) { return v === 'exam' ? 'warning' : v === 'textbook' ? 'primary' : 'info' }
function statusLabel(v) { return statusMap[v] || v }
function statusTag(v) { return v === 'success' ? 'success' : v === 'failed' ? 'danger' : v === 'parsing' ? 'warning' : 'info' }

onMounted(() => {
  fetchDocs()
  fetchSubjects()
})

async function fetchDocs() {
  loading.value = true
  try {
    const params = { page: page.value, size: size.value, ...filter }
    Object.keys(params).forEach(k => { if (params[k] === '' || params[k] === null) delete params[k] })
    const res = await getDocumentList(params)
    if (res.code === 200) {
      documents.value = res.data.items
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

async function fetchSubjects() {
  try {
    const res = await getSubjects()
    if (res.code === 200) {
      subjects.value = res.data.map(s => ({ id: s.id, name: s.name }))
    }
  } catch {}
}

function showUpload() {
  uploadVisible.value = true
  uploadForm.subject_id = null
  uploadForm.title = ''
  uploadForm.doc_type = 'textbook'
  uploadForm.year = null
  uploadForm.question_type = ''
  selectedFile.value = null
}

async function handleAddSubject() {
  try {
    const { value } = await ElMessageBox.prompt('请输入新科目名称', '新增科目', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '科目名称不能为空',
    })
    if (!value?.trim()) return
    const res = await createSubject({ name: value.trim(), description: '' })
    if (res.code === 200) {
      ElMessage.success('科目创建成功')
      await fetchSubjects()
      uploadForm.subject_id = res.data.id
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch { }
}

function onFileChange(_, files) {
  if (files.length) {
    selectedFile.value = files[0].raw
  } else {
    selectedFile.value = null
  }
}

async function handleUpload() {
  const valid = await uploadFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('subject_id', uploadForm.subject_id)
    fd.append('title', uploadForm.title)
    fd.append('doc_type', uploadForm.doc_type)
    if (uploadForm.year) fd.append('year', uploadForm.year)
    fd.append('question_type', uploadForm.question_type || '')
    fd.append('file', selectedFile.value)
    const res = await uploadDocument(fd)
    if (res.code === 200) {
      ElMessage.success('上传成功，开始解析')
      uploadVisible.value = false
      fetchDocs()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleReparse(row) {
  await reparseDocument(row.id)
  ElMessage.success('已触发重新解析')
  fetchDocs()
}

async function handleDelete(row) {
  await deleteDocument(row.id)
  ElMessage.success('已删除')
  fetchDocs()
}

async function viewChunks(row) {
  chunkVisible.value = true
  chunkLoading.value = true
  try {
    const res = await getDocumentChunks(row.id)
    if (res.code === 200) chunks.value = res.data
  } finally {
    chunkLoading.value = false
  }
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.filter-bar { margin-bottom: 16px; }
.filter-bar .el-form-item { margin-bottom: 0; }
.pagination-wrap { margin-top: 20px; display: flex; justify-content: center; }
.chunk-item { background: #f9f9f9; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.chunk-header { font-weight: 600; font-size: 13px; color: #606266; margin-bottom: 6px; }
.chunk-content { font-size: 13px; line-height: 1.6; color: #303133; white-space: pre-wrap; }
</style>
