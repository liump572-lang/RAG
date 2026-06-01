import request from './request'

export function askQuestion() {
  return `${request.defaults.baseURL}/qa/ask`
}

export function getConversations(params) {
  return request.get('/qa/conversations', { params })
}

export function getMessages(conversationId) {
  return request.get(`/qa/conversations/${conversationId}/messages`)
}

export function deleteConversation(id) {
  return request.delete(`/qa/conversations/${id}`)
}

export function submitFeedback(messageId, score) {
  return request.post(`/qa/feedback/${messageId}`, { score })
}
