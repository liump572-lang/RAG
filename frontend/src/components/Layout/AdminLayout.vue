<template>
  <div class="app-layout">
    <div class="bg-effects">
      <div class="orb"></div>
      <div class="orb"></div>
      <div class="orb"></div>
    </div>
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">Q</div>
        <span class="brand">QnA 智能问答</span>
      </div>
      <nav class="sidebar-menu">
        <div class="menu-group">管理后台</div>
        <router-link v-for="item in menuItems" :key="item.path" :to="item.path"
          class="menu-item" :class="{ active: activeMenu === item.path }">
          <span class="icon" v-html="item.icon"></span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="avatar">{{ auth.user?.username?.[0] || '管' }}</div>
        <div class="info">
          <span class="name">{{ auth.user?.username || '管理员' }}</span>
          <span class="role">admin</span>
        </div>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div class="topbar-title" v-html="currentTitle"></div>
        <div class="topbar-actions">
          <button class="logout-btn" @click="handleLogout">退出登录</button>
        </div>
      </header>
      <div class="content">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => route.path)

const menuItems = [
  { path: '/admin/dashboard', label: '工作台', icon: '&#128202;' },
  { path: '/admin/knowledge-base', label: '知识库管理', icon: '&#128451;' },
  { path: '/admin/subjects', label: '科目管理', icon: '&#128218;' },
  { path: '/admin/users', label: '用户管理', icon: '&#128101;' },
  { path: '/admin/knowledge-graph', label: '知识图谱', icon: '&#128200;' },
  { path: '/admin/notes-review', label: '心得审核', icon: '&#9989;' },
  { path: '/admin/qa', label: '智能问答', icon: '&#128172;' },
  { path: '/admin/system-config', label: '系统设置', icon: '&#9881;' },
]

const pageTitles = {
  '/admin/dashboard': '&#128202; 工作台',
  '/admin/knowledge-base': '&#128451; 知识库管理',
  '/admin/subjects': '&#128218; 科目管理',
  '/admin/users': '&#128101; 用户管理',
  '/admin/knowledge-graph': '&#128200; 知识图谱',
  '/admin/notes-review': '&#9989; 心得审核',
  '/admin/qa': '&#128172; 智能问答',
  '/admin/system-config': '&#9881; 系统设置',
}

const currentTitle = computed(() => pageTitles[route.path] || '')

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
</style>
