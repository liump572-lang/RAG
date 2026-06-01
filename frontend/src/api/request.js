import axios from 'axios'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

request.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshed = await tryRefreshToken()
      if (refreshed) {
        const token = localStorage.getItem('access_token')
        error.config.headers.Authorization = `Bearer ${token}`
        return request(error.config)
      }
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

async function tryRefreshToken() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return false
  try {
    const res = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
    if (res.data.code === 200) {
      localStorage.setItem('access_token', res.data.data.access_token)
      localStorage.setItem('refresh_token', res.data.data.refresh_token)
      return true
    }
  } catch {
    return false
  }
  return false
}

export default request
