<template>
  <div class="login-page">
    <div class="bg-effects">
      <div class="orb"></div>
      <div class="orb"></div>
      <div class="orb"></div>
    </div>
    <div class="login-card">
      <h1>⚡ QnA · 智能问答</h1>
      <p class="sub">计算机学科知识点智能问答系统</p>
      <p v-if="isRegister" style="color:var(--primary);font-size:13px;text-align:center;margin-bottom:16px">📝 注册新账号</p>
      <el-form ref="formRef" :model="form" :rules="rules" @keyup.enter="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </div>
        <div class="form-group">
          <label>密码</label>
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </div>
        <div class="form-group" v-if="isRegister">
          <label>登录身份</label>
          <el-select v-model="role" style="width:100%">
            <el-option value="admin" label="管理员" />
            <el-option value="user" label="普通用户（学生）" />
          </el-select>
        </div>
        <el-button type="primary" class="btn btn-primary btn-block" :loading="loading" @click="handleLogin">
          {{ isRegister ? '📝 注 册' : '➜ 登 录' }}
        </el-button>
      </el-form>
      <div class="login-footer">
        <a @click="toggleMode">{{ isRegister ? '已有账号？去登录' : '注册账号' }}</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { register } from '@/api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const role = ref('admin')
const loading = ref(false)
const isRegister = ref(false)
const formRef = ref(null)

const form = reactive({
  username: 'admin',
  password: 'admin123',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function toggleMode() {
  isRegister.value = !isRegister.value
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    if (isRegister.value) {
      const res = await register({
        username: form.username,
        password: form.password,
        email: `${form.username}@kqa.com`,
        role: role.value,
      })
      if (res.code === 200) {
        ElMessage.success('注册成功，请登录')
        isRegister.value = false
      }
    } else {
      const ok = await auth.login({ username: form.username, password: form.password })
      if (ok) {
        ElMessage.success('登录成功')
        router.push(auth.isAdmin ? '/admin/dashboard' : '/user/qa')
      } else {
        ElMessage.error('用户名或密码错误')
      }
    }
  } catch (e) {
    const detail = e.response?.data?.detail
    ElMessage.error(detail?.message || e.response?.data?.message || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  position: relative;
  z-index: 1;
  padding: 20px;
  background: var(--bg);
}
.login-card {
  background: rgba(30, 30, 54, 0.85);
  backdrop-filter: blur(24px);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px;
  width: 420px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  animation: fadeUp 0.6s ease;
}
.login-card h1 {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary), var(--accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 4px;
  text-align: center;
}
.login-card .sub {
  color: var(--text2);
  margin-bottom: 28px;
  font-size: 14px;
  text-align: center;
}
.login-footer {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--text3);
}
.login-footer a {
  color: var(--primary);
  text-decoration: none;
  cursor: pointer;
  transition: color 0.2s;
}
.login-footer a:hover {
  color: var(--accent);
}
</style>
