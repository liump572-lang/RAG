<template>
  <div class="card">
    <div class="card-header">
      <span>科目列表</span>
      <button class="btn btn-primary" @click="openDialog(null)">+ 新增科目</button>
    </div>
    <div class="card-body">
      <el-table :data="subjects" stripe style="width: 100%" empty-text="暂无科目">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="科目名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
        <el-table-column label="内置" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_built_in ? 'primary' : 'info'" size="small">{{ row.is_built_in ? '内置' : '自定义' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文档数" width="100" align="center">
          <template #default="{ row }">
            <span class="badge">{{ docCounts[row.id] || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDialog(row)">编辑</el-button>
            <el-button v-if="!row.is_built_in" type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑科目' : '新增科目'" width="500px" :close-on-click-modal="false"
      class="custom-dialog">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="科目名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入科目名称" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" placeholder="请输入科目描述（选填）" type="textarea" :rows="3" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="btn" @click="dialogVisible = false">取消</button>
        <button class="btn btn-primary" @click="handleSave">保存</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSubjects, createSubject, updateSubject, deleteSubject } from '@/api/subjects'
import { ElMessage, ElMessageBox } from 'element-plus'

const subjects = ref([])
const docCounts = ref({})
const dialogVisible = ref(false)
const editing = ref(null)
const formRef = ref(null)
const form = ref({ name: '', description: '' })
const rules = {
  name: [{ required: true, message: '请输入科目名称', trigger: 'blur' }],
}

async function fetchSubjects() {
  const res = await getSubjects()
  if (res.code === 200) {
    subjects.value = res.data
  }
}

function openDialog(row) {
  if (row) {
    editing.value = row.id
    form.value = { name: row.name, description: row.description || '' }
  } else {
    editing.value = null
    form.value = { name: '', description: '' }
  }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  let res
  if (editing.value) {
    res = await updateSubject(editing.value, form.value)
  } else {
    res = await createSubject(form.value)
  }
  if (res.code === 200) {
    ElMessage.success(editing.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    await fetchSubjects()
  } else {
    ElMessage.error(res.message || '操作失败')
  }
}

function handleDelete(row) {
  ElMessageBox.confirm(`确定删除科目「${row.name}」？`, '确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    const res = await deleteSubject(row.id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      await fetchSubjects()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  }).catch(() => {})
}

onMounted(fetchSubjects)
</script>
