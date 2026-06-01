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
        <div class="menu-group">学习中心</div>
        <router-link v-for="item in menuItems" :key="item.path" :to="item.path"
          class="menu-item" :class="{ active: activeMenu.startsWith(item.path) }">
          <span class="icon" v-html="item.icon"></span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="avatar">{{ auth.user?.username?.[0] || '学' }}</div>
        <div class="info">
          <span class="name">{{ auth.user?.username || '学生' }}</span>
          <span class="role">user</span>
        </div>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div class="topbar-title" v-html="currentTitle"></div>
        <div class="topbar-actions">
          <!-- 通知铃铛 -->
          <el-popover
            placement="bottom-end" :width="360" trigger="click"
            @show="fetchNotifications()"
          >
            <template #reference>
              <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="notif-badge">
                <button class="notif-bell" title="消息通知">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                  </svg>
                </button>
              </el-badge>
            </template>
            <div class="notif-popover">
              <div class="notif-pop-header">
                <span class="notif-title">消息通知</span>
                <button v-if="unreadCount > 0" class="notif-mark-all" @click="handleMarkAllRead">全部已读</button>
              </div>
              <div v-if="notifications.length === 0" class="notif-empty">暂无消息</div>
              <div v-else class="notif-list">
                <div
                  v-for="n in notifications" :key="n.id"
                  :class="['notif-item', { unread: !n.is_read }]"
                  @click="handleClickNotif(n)"
                >
                  <div class="notif-dot" v-if="!n.is_read"></div>
                  <div class="notif-body">
                    <div class="notif-item-title">{{ n.title }}</div>
                    <div class="notif-item-content" v-if="n.content">{{ n.content }}</div>
                    <div class="notif-item-time">{{ formatNotifTime(n.created_at) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </el-popover>
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getNotifications, getUnreadCount, markRead, markAllRead } from '@/api/notification'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => route.path)

const menuItems = [
  { path: '/user/qa', label: '智能问答', icon: '&#128172;' },
  { path: '/user/notes', label: '心得广场', icon: '&#128214;' },
  { path: '/user/my-notes', label: '我的心得', icon: '&#128221;' },
  { path: '/user/wrong-questions', label: '错题本', icon: '&#128683;' },
]

const pageTitles = {
  '/user/qa': '&#128172; 智能问答',
  '/user/notes': '&#128214; 心得广场',
  '/user/my-notes': '&#128221; 我的心得',
  '/user/notes/publish': '&#128221; 发布心得',
  '/user/notes/publish/': '&#128221; 编辑心得',
  '/user/notes/': '&#128214; 心得详情',
  '/user/wrong-questions': '&#128683; 错题本',
}

const currentTitle = computed(() => {
  for (const [prefix, title] of Object.entries(pageTitles)) {
    if (route.path.startsWith(prefix)) return title
  }
  return ''
})

// ── 通知 ──
const notifications = ref([])
const unreadCount = ref(0)
const notifLoaded = ref(false)

async function fetchNotifications() {
  if (!auth.isLoggedIn) return
  try {
    const [notifRes, countRes] = await Promise.all([
      getNotifications({ page: 1, size: 20 }),
      getUnreadCount(),
    ])
    if (notifRes.code === 200) notifications.value = notifRes.data.items
    if (countRes.code === 200) unreadCount.value = countRes.data.count
    notifLoaded.value = true
  } catch { /* 静默失败，避免 401 触发全局拦截器跳转 */ }
}

async function handleMarkAllRead() {
  try {
    await markAllRead()
    unreadCount.value = 0
    notifications.value.forEach(n => n.is_read = true)
  } catch { /* ignore */ }
}

async function handleClickNotif(n) {
  if (!n.is_read) {
    try {
      await markRead(n.id)
      n.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch { /* ignore */ }
  }
}

function formatNotifTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = now - d
  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return Math.floor(diff / 60_000) + ' 分钟前'
  if (diff < 86400_000) return Math.floor(diff / 3600_000) + ' 小时前'
  return d.toLocaleDateString('zh-CN')
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  fetchNotifications()
})
</script>

<style scoped>
/* ── 通知 ── */
.notif-bell {
  background: none; border: none; cursor: pointer; color: var(--text2);
  padding: 6px; border-radius: 8px; display: flex; align-items: center;
  transition: all 0.15s;
}
.notif-bell:hover { background: rgba(124,58,237,0.1); color: var(--primary); }
.notif-badge { margin-right: 6px; }

.notif-popover { max-height: 400px; display: flex; flex-direction: column; }
.notif-pop-header {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 10px; border-bottom: 1px solid var(--border); margin-bottom: 6px;
}
.notif-title { font-size: 14px; font-weight: 600; }
.notif-mark-all { background: none; border: none; color: var(--primary); cursor: pointer; font-size: 12px; }
.notif-empty { text-align: center; padding: 30px 0; color: var(--text3); font-size: 13px; }
.notif-list { overflow-y: auto; max-height: 330px; }
.notif-item {
  display: flex; align-items: flex-start; gap: 8px; padding: 10px 6px;
  cursor: pointer; border-radius: 6px; transition: background 0.1s;
}
.notif-item:hover { background: rgba(0,0,0,0.03); }
.notif-item.unread { background: rgba(124,58,237,0.04); }
.notif-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--primary); margin-top: 5px; flex-shrink: 0; }
.notif-body { flex: 1; min-width: 0; }
.notif-item-title { font-size: 13px; font-weight: 500; color: var(--text); margin-bottom: 2px; }
.notif-item-content { font-size: 12px; color: var(--text2); white-space: pre-line; margin-bottom: 2px; }
.notif-item-time { font-size: 11px; color: var(--text3); }
</style>
