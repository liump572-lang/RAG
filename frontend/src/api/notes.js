import request from './request'

export function getNotes(params) {
  return request.get('/notes', { params })
}

export function getNote(id) {
  return request.get(`/notes/${id}`)
}

export function createNote(data) {
  return request.post('/notes', data)
}

export function updateNote(id, data) {
  return request.put(`/notes/${id}`, data)
}

export function deleteNote(id) {
  return request.delete(`/notes/${id}`)
}

export function toggleLike(id) {
  return request.post(`/notes/${id}/like`)
}

export function toggleFavorite(id) {
  return request.post(`/notes/${id}/favorite`)
}

export function getComments(id) {
  return request.get(`/notes/${id}/comments`)
}

export function addComment(id, data) {
  return request.post(`/notes/${id}/comments`, data)
}

export function getReviewList(params) {
  return request.get('/notes/admin/review', { params })
}

export function reviewNote(id, data) {
  return request.post(`/notes/admin/review/${id}`, data)
}

export function togglePin(id) {
  return request.post(`/notes/admin/pin/${id}`)
}

export function batchReview(data) {
  return request.post('/notes/admin/review/batch', data)
}

export function aiReviewAllPending() {
  return request.post('/notes/admin/review/ai-all')
}

export function getNoteStatus(id) {
  return request.get(`/notes/${id}/status`)
}

export function aiReview(id) {
  return request.post(`/notes/admin/ai-review/${id}`)
}

export function getMyCounts() {
  return request.get('/notes/my-counts')
}
