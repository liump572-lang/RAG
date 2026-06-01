import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/admin',
    component: () => import('@/components/Layout/AdminLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/Dashboard.vue'),
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/UserManage.vue'),
      },
      {
        path: 'knowledge-base',
        name: 'AdminKnowledgeBase',
        component: () => import('@/views/admin/KnowledgeBase.vue'),
      },
      {
        path: 'knowledge-graph',
        name: 'AdminKnowledgeGraph',
        component: () => import('@/views/admin/KnowledgeGraph.vue'),
      },
      {
        path: 'subjects',
        name: 'AdminSubjects',
        component: () => import('@/views/admin/SubjectManage.vue'),
      },
      {
        path: 'notes-review',
        name: 'AdminNotesReview',
        component: () => import('@/views/admin/NoteReview.vue'),
      },
      {
        path: 'qa',
        name: 'AdminQa',
        component: () => import('@/views/user/QaChat.vue'),
      },
      {
        path: 'system-config',
        name: 'AdminSystemConfig',
        component: () => import('@/views/admin/SystemConfig.vue'),
      },
    ],
  },
  {
    path: '/user',
    component: () => import('@/components/Layout/UserLayout.vue'),
    meta: { requiresAuth: true, role: 'user' },
    children: [
      { path: '', redirect: '/user/qa' },
      {
        path: 'qa',
        name: 'UserQa',
        component: () => import('@/views/user/QaChat.vue'),
      },
      {
        path: 'notes',
        name: 'UserNotes',
        component: () => import('@/views/user/StudyNotes.vue'),
      },
      {
        path: 'my-notes',
        name: 'MyNotes',
        component: () => import('@/views/user/MyNotes.vue'),
      },
      {
        path: 'notes/publish',
        name: 'NotePublish',
        component: () => import('@/views/user/NotePublish.vue'),
      },
      {
        path: 'notes/publish/:id',
        name: 'NoteEdit',
        component: () => import('@/views/user/NotePublish.vue'),
      },
      {
        path: 'notes/:id',
        name: 'NoteDetail',
        component: () => import('@/views/user/NoteDetail.vue'),
      },
      {
        path: 'wrong-questions',
        name: 'WrongQuestions',
        component: () => import('@/views/user/WrongQuestions.vue'),
      },
    ],
  },
  { path: '/', redirect: '/login' },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && auth.isLoggedIn) {
    next(auth.isAdmin ? '/admin/dashboard' : '/user/qa')
  } else if (to.meta.role && auth.user?.role !== to.meta.role) {
    next(auth.isAdmin ? '/admin/dashboard' : '/user/qa')
  } else {
    next()
  }
})

export default router
