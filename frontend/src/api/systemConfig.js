import request from './request'

export function getConfigs(params) {
  return request.get('/admin/system/configs', { params })
}

export function createConfig(data) {
  return request.post('/admin/system/configs', data)
}

export function updateConfig(id, data) {
  return request.put(`/admin/system/configs/${id}`, data)
}

export function deleteConfig(id) {
  return request.delete(`/admin/system/configs/${id}`)
}

export function getModels() {
  return request.get('/admin/system/models')
}

export function getSettings() {
  return request.get('/admin/system/settings')
}

export function saveSettings(data) {
  return request.put('/admin/system/settings', data)
}
