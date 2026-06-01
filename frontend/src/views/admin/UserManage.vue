<template>
  <div class="user-manage">
    <el-card>
      <div class="page-header">
        <h2>用户管理</h2>
        <el-button type="primary" @click="showCreate">新增用户</el-button>
      </div>

      <el-table :data="users" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="role" label="角色" width="80">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">
              {{ row.role === 'admin' ? '管理员' : '学生' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEdit(row)">编辑</el-button>
            <el-button size="small" @click="handleToggleStatus(row)">
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-popconfirm title="确认重置密码为 123456？" @confirm="handleResetPwd(row)">
              <template #reference>
                <el-button size="small">重置密码</el-button>
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
          @current-change="fetchUsers"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role">
            <el-option label="学生" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUserList, createUser, updateUser, toggleUserStatus, resetUserPassword, deleteUser } from '@/api/user'

const users = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const size = ref(20)

const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const formRef = ref(null)
const editingId = ref(null)

const form = ref({
  username: '',
  email: '',
  role: 'user',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

onMounted(() => fetchUsers())

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUserList({ page: page.value, size: size.value })
    if (res.code === 200) {
      users.value = res.data.items
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = { username: '', email: '', role: 'user', password: '' }
  dialogVisible.value = true
}

function showEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  form.value = { username: row.username, email: row.email, role: row.role, password: '' }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value) {
      await updateUser(editingId.value, { username: form.value.username, email: form.value.email, role: form.value.role })
      ElMessage.success('更新成功')
    } else {
      await createUser(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } finally {
    saving.value = false
  }
}

async function handleToggleStatus(row) {
  await toggleUserStatus(row.id)
  ElMessage.success('操作成功')
  fetchUsers()
}

async function handleResetPwd(row) {
  await resetUserPassword(row.id, { new_password: '123456' })
  ElMessage.success('密码已重置为 123456')
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.pagination-wrap { margin-top: 20px; display: flex; justify-content: center; }
</style>
