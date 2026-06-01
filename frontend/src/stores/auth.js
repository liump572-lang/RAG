import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshTokenVal = ref(localStorage.getItem('refresh_token') || '')

  const isLoggedIn = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isUser = computed(() => user.value?.role === 'user')

  async function login(credentials) {
    const res = await loginApi(credentials)
    if (res.code === 200) {
      accessToken.value = res.data.access_token
      refreshTokenVal.value = res.data.refresh_token
      localStorage.setItem('access_token', res.data.access_token)
      localStorage.setItem('refresh_token', res.data.refresh_token)
      const meRes = await getCurrentUser()
      if (meRes.code === 200) {
        user.value = meRes.data
        localStorage.setItem('user', JSON.stringify(meRes.data))
      }
      return true
    }
    return false
  }

  function logout() {
    user.value = null
    accessToken.value = ''
    refreshTokenVal.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  }

  async function fetchUser() {
    const res = await getCurrentUser()
    if (res.code === 200) {
      user.value = res.data
      localStorage.setItem('user', JSON.stringify(res.data))
    }
    return user.value
  }

  return { user, accessToken, refreshTokenVal, isLoggedIn, isAdmin, isUser, login, logout, fetchUser }
})
