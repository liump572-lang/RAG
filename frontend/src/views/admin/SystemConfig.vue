<template>
  <div class="config-page">
    <div class="page-toolbar">
      <h2>系统设置</h2>
      <span class="toolbar-hint">修改将在下次提问时生效</span>
    </div>

    <!-- 模型选择 -->
    <el-card class="section-card">
      <template #header><span class="card-title">模型选择</span></template>
      <div class="model-grid">
        <div
          v-for="m in models" :key="m.value"
          :class="['model-card', { active: selectedModel === m.value, current: savedModel === m.value }]"
          @click="selectedModel = m.value"
        >
          <div class="model-name">{{ m.label }}</div>
          <div class="model-desc">{{ m.description }}</div>
          <div class="model-value">{{ m.value }}</div>
          <span v-if="savedModel === m.value" class="model-badge">当前使用</span>
          <span v-else-if="selectedModel === m.value" class="model-badge pending">待保存</span>
        </div>
      </div>
      <div v-if="selectedModel !== savedModel" style="margin-top:14px;display:flex;align-items:center;gap:10px">
        <el-button type="primary" :loading="savingModel" @click="saveModel">保存模型设置</el-button>
        <el-button size="small" @click="selectedModel = savedModel">取消</el-button>
      </div>
    </el-card>

    <!-- API 配置 -->
    <el-card class="section-card">
      <template #header><span class="card-title">API 配置</span></template>
      <el-form :model="apiForm" label-width="110px">
        <el-form-item label="API Base URL">
          <el-input v-model="apiForm.api_base" placeholder="https://api.deepseek.com/v1" />
        </el-form-item>
        <el-form-item label="API Key">
          <div style="display:flex;flex-direction:column;gap:6px;width:100%">
            <div style="display:flex;gap:8px;align-items:center">
              <el-input
                v-model="apiForm.api_key"
                type="password"
                placeholder="输入新 API Key 以更换"
                show-password
                style="flex:1"
              />
              <el-button
                size="small"
                @click="apiForm.api_key = ''; apiKeyChanged = false"
                :disabled="!apiKeyChanged"
              >
                重置
              </el-button>
            </div>
            <span class="field-hint">
              当前：{{ apiMasked || '未配置' }}
              <template v-if="apiKeyChanged">（已修改，保存后生效）</template>
            </span>
          </div>
        </el-form-item>
        <el-form-item label="Embedding 模型">
          <el-input :model-value="embeddingModel" disabled>
            <template #suffix><span style="color:var(--text3);font-size:12px">只读</span></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingApi" @click="saveApiSettings" :disabled="!apiFormChanged">
            保存 API 设置
          </el-button>
          <span v-if="!apiFormChanged" style="font-size:12px;color:var(--text3);margin-left:8px">无修改</span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 高级配置 -->
    <el-card class="section-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span class="card-title">高级配置</span>
          <el-button size="small" @click="showAdd = true">新增配置</el-button>
        </div>
      </template>
      <el-table :data="list" v-loading="loading" empty-text="暂无配置项" stripe>
        <el-table-column prop="config_key" label="配置键" min-width="180">
          <template #default="{ row }">
            <code style="font-size:12px">{{ row.config_key }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="config_value" label="配置值" min-width="220">
          <template #default="{ row }">
            <span v-if="isSecretKey(row.config_key)">{{ maskValue(row.config_value) }}</span>
            <span v-else>{{ row.config_value }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="150">
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editRow(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增配置对话框 -->
    <el-dialog v-model="showAdd" title="新增配置" width="500px">
      <el-form :model="addForm" label-width="80px" ref="addFormRef" :rules="addRules">
        <el-form-item label="配置键" prop="config_key">
          <el-input v-model="addForm.config_key" placeholder="如 embedding_model" />
        </el-form-item>
        <el-form-item label="配置值" prop="config_value">
          <el-input v-model="addForm.config_value" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="addForm.description" placeholder="可选说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleAdd">保存</el-button>
      </template>
    </el-dialog>

    <!-- 编辑配置对话框 -->
    <el-dialog v-model="showEdit" title="编辑配置" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="配置键">
          <el-input :model-value="editForm.config_key" disabled />
        </el-form-item>
        <el-form-item label="配置值">
          <el-input v-model="editForm.config_value" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="editForm.description" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getConfigs, createConfig, updateConfig, deleteConfig, getModels, getSettings, saveSettings } from '@/api/systemConfig'

// ── 模型选择 ──
const models = ref([])
const selectedModel = ref('')       // 用户当前点击的模型（未保存）
const savedModel = ref('')          // 数据库中实际保存的模型
const savingModel = ref(false)

// ── API 配置 ──
const apiForm = reactive({ api_base: '', api_key: '' })
const apiSavedBase = ref('')
const apiMasked = ref('')
const embeddingModel = ref('')
const apiKeyChanged = ref(false)
const savingApi = ref(false)

const apiFormChanged = computed(() => {
  return apiForm.api_base !== apiSavedBase.value || apiKeyChanged.value
})

// ── 高级配置 ──
const list = ref([])
const loading = ref(false)
const saving = ref(false)
const showAdd = ref(false)
const showEdit = ref(false)
const editTarget = ref(null)
const addFormRef = ref(null)

const addForm = reactive({ config_key: '', config_value: '', description: '' })
const editForm = reactive({ config_key: '', config_value: '', description: '' })
const addRules = {
  config_key: [{ required: true, message: '请输入配置键', trigger: 'blur' }],
  config_value: [{ required: true, message: '请输入配置值', trigger: 'blur' }],
}

onMounted(() => {
  Promise.all([fetchModels(), fetchSettings(), fetchList()])
})

// ── API calls ──
async function fetchModels() {
  try {
    const res = await getModels()
    if (res.code === 200) models.value = res.data
  } catch { /* ignore */ }
}

async function fetchSettings() {
  try {
    const res = await getSettings()
    if (res.code === 200) {
      savedModel.value = res.data.llm_model || ''
      selectedModel.value = savedModel.value
      apiSavedBase.value = res.data.api_base || ''
      apiForm.api_base = apiSavedBase.value
      apiForm.api_key = ''
      apiKeyChanged.value = false
      apiMasked.value = res.data.api_key_masked || ''
      embeddingModel.value = res.data.embedding_model || ''
    }
  } catch { /* ignore */ }
}

async function fetchList() {
  loading.value = true
  try {
    const res = await getConfigs()
    if (res.code === 200) list.value = res.data
  } finally {
    loading.value = false
  }
}

// ── Model save ──
async function saveModel() {
  if (selectedModel.value === savedModel.value) return
  savingModel.value = true
  try {
    await saveSettings({ llm_model: selectedModel.value })
    savedModel.value = selectedModel.value
    ElMessage.success('模型已切换，下次提问时生效')
    fetchList()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingModel.value = false
  }
}

// ── API settings save ──
async function saveApiSettings() {
  savingApi.value = true
  try {
    const payload = { api_base: apiForm.api_base }
    if (apiKeyChanged.value) payload.api_key = apiForm.api_key
    await saveSettings(payload)
    ElMessage.success('API 设置已保存，下次提问时生效')
    fetchSettings()
    fetchList()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingApi.value = false
  }
}

// Watch API key field for changes
import { watch } from 'vue'
watch(() => apiForm.api_key, (val) => {
  apiKeyChanged.value = val !== ''
})

// ── Helpers ──
function isSecretKey(key) {
  return key && (key.includes('api_key') || key.includes('secret') || key.includes('password'))
}

function maskValue(val) {
  if (!val) return ''
  if (val.length <= 12) return '****'
  return val.slice(0, 6) + '****' + val.slice(-4)
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

// ── Advanced config operations ──
function editRow(row) {
  editTarget.value = row
  editForm.config_key = row.config_key
  editForm.config_value = row.config_value
  editForm.description = row.description
  showEdit.value = true
}

async function handleAdd() {
  const valid = await addFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await createConfig({ config_key: addForm.config_key, config_value: addForm.config_value, description: addForm.description })
    ElMessage.success('已创建')
    showAdd.value = false
    addForm.config_key = ''; addForm.config_value = ''; addForm.description = ''
    fetchList()
  } finally {
    saving.value = false
  }
}

async function handleEdit() {
  saving.value = true
  try {
    await updateConfig(editTarget.value.id, { config_value: editForm.config_value, description: editForm.description })
    ElMessage.success('已更新')
    showEdit.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除此配置？')
    await deleteConfig(row.id)
    ElMessage.success('已删除')
    fetchList()
  } catch { /* user cancelled */ }
}
</script>

<style scoped>
.page-toolbar { display:flex; align-items:baseline; gap:16px; margin-bottom:20px; }
.page-toolbar h2 { margin:0; }
.toolbar-hint { font-size:12px; color:var(--text3); }
.section-card { margin-bottom:20px; }
.card-title { font-size:15px; font-weight:600; }
.field-hint { font-size:12px; color:var(--text2); }

/* ── Model grid ── */
.model-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); gap:12px; }
.model-card {
  border:2px solid var(--border);
  border-radius:10px;
  padding:16px;
  cursor:pointer;
  transition:all 0.2s;
  position:relative;
}
.model-card:hover { border-color:var(--primary); background:rgba(124,58,237,0.05); }
.model-card.active { border-color:var(--primary); background:rgba(124,58,237,0.08); }
.model-card.current { border-color:var(--primary); background:rgba(124,58,237,0.12); }
.model-name { font-size:15px; font-weight:600; color:var(--text); margin-bottom:4px; }
.model-desc { font-size:12px; color:var(--text2); margin-bottom:6px; }
.model-value { font-size:11px; color:var(--text3); font-family:monospace; }
.model-badge {
  position:absolute; top:8px; right:10px;
  font-size:11px; color:var(--primary); font-weight:600;
}
.model-badge.pending { color:#e6a23c; }
</style>
