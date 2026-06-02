<template>
  <div class="chat-layout">
    <div class="chat-sidebar" @scroll.passive="handleConversationScroll">
      <div class="chat-list-header">
        <span>对话列表</span>
        <button class="btn btn-primary btn-xs" @click="newConversation">+ 新建</button>
      </div>
      <div v-for="c in conversations" :key="c.id"
        :class="['chat-item', { active: c.id === activeConvId }]"
        @click="switchConversation(c.id)">
        <div class="title">{{ c.title }}</div>
        <div class="sub">{{ c.message_count }} 条消息</div>
      </div>
      <div v-if="!conversations.length" style="text-align:center;padding:24px;color:var(--text3);font-size:13px">暂无对话</div>
      <div v-else-if="loadingConversations" class="chat-list-status">加载中...</div>
      <div v-else-if="!hasMoreConversations" class="chat-list-status">已加载全部历史对话</div>
    </div>

    <div class="chat-main">
      <div class="chat-msgs" ref="messagesRef">
        <div v-if="!messages.length && !streaming" class="welcome">
          <div style="text-align:center;padding-top:60px">
            <div style="font-size:40px;margin-bottom:12px;opacity:0.6">💬</div>
            <h2 style="font-size:22px;color:var(--text);font-weight:700;margin-bottom:8px">有什么想问的？</h2>
            <p style="color:var(--text2);margin-bottom:20px;font-size:14px">计算机网络 · 操作系统 · 数据库 · 更多...</p>
            <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
              <span v-for="s in suggestions" :key="s"
                class="tag tag-purple" style="cursor:pointer;padding:6px 14px;font-size:13px"
                @click="question = s; sendMessage()">{{ s }}</span>
            </div>
          </div>
        </div>

        <TransitionGroup name="msg">
          <div v-for="(msg, i) in messages" :key="msg.id || i"
            :class="['chat-msg', msg.role === 'user' ? 'self' : 'bot']">
            <div class="msg-avatar" :style="{ background: msg.role === 'user' ? 'linear-gradient(135deg,var(--primary),var(--accent))' : 'linear-gradient(135deg,#06b6d4,#818cf8)' }">
              {{ msg.role === 'user' ? '我' : 'AI' }}
            </div>
            <div class="msg-bubble">
              <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
              <div class="msg-sources" v-if="msg.role === 'assistant' && msg.sources && getNoteSources(msg.sources).length">
                <div class="sources-title">📚 参考来源</div>
                <div class="source-group" v-if="getOwnNoteSources(msg.sources).length">
                  <div class="source-group-title">📋 我的心得</div>
                  <div v-for="src in getOwnNoteSources(msg.sources)" :key="src.title" class="source-item own-note">
                    <span class="source-name">{{ src.title || '无标题' }}</span>
                    <el-tag :type="noteStatusTagType(src.status)" size="small">{{ noteStatusLabel(src.status) }}</el-tag>
                    <span v-if="src.status === 'rejected' && src.reject_reason" class="reject-reason">原因：{{ src.reject_reason }}</span>
                  </div>
                </div>
                <div class="source-group" v-if="getOtherNoteSources(msg.sources).length">
                  <div class="source-group-title">🌍 他人的心得</div>
                  <div v-for="src in getOtherNoteSources(msg.sources)" :key="src.title" class="source-item">
                    <span class="source-name">{{ src.title || '无标题' }}</span>
                    <span class="source-author">{{ src.author || '未知用户' }}</span>
                  </div>
                </div>
              </div>
              <div class="feedback" v-if="msg.role === 'assistant' && msg.id">
                <button @click="handleFeedback(msg.id, 5)" :style="{ borderColor: feedbackMap[msg.id] >= 4 ? 'var(--primary)' : '', color: feedbackMap[msg.id] >= 4 ? 'var(--primary)' : '' }">👍 有用</button>
                <button @click="handleFeedback(msg.id, 1)" :style="{ borderColor: feedbackMap[msg.id] <= 2 ? 'var(--danger)' : '', color: feedbackMap[msg.id] <= 2 ? 'var(--danger)' : '' }">👎 无用</button>
                <button v-if="auth.isUser" class="wrong-btn" @click="addToWrongBook(msg, i)">📝 加入错题本</button>
              </div>
            </div>
          </div>
        </TransitionGroup>

        <div v-if="streaming" class="chat-msg bot">
          <div class="msg-avatar" style="background:linear-gradient(135deg,#06b6d4,#818cf8)">AI</div>
          <div class="msg-bubble">
            <div class="markdown-body" v-html="renderMarkdown(streamContent, { enableMermaid: false })"></div>
            <span v-if="!streamContent" style="color:var(--text3);font-size:16px">思考中<span class="dot-pulse"></span></span>
          </div>
        </div>
      </div>

      <div class="chat-input-wrap">
        <input v-model="question" placeholder="输入你的问题..." @keyup.enter="sendMessage" :disabled="streaming">
        <button class="send-btn" @click="sendMessage" :disabled="streaming || !question.trim()">➤</button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, ref, onMounted, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { askQuestion, getConversations, getMessages, submitFeedback } from '@/api/qa'
import { createWrongQuestion } from '@/api/wrongQuestions'
import { useAutoRefresh } from '@/composables/useAutoRefresh'
import { initializeMermaid, renderMarkdown } from '@/utils/markdown'

const auth = useAuthStore()
const messagesRef = ref(null)
const activeConvId = ref(null)
const activeConvSubjectId = ref(null)
const conversations = ref([])
const conversationPage = ref(1)
const conversationTotal = ref(0)
const loadingConversations = ref(false)
const loadingMessages = ref(false)
const messages = ref([])
const question = ref('')
const streaming = ref(false)
const sendingMessage = ref(false)
const streamContent = ref('')
const feedbackMap = ref({})

const suggestions = [
  '什么是 OSI 七层模型？',
  'TCP 和 UDP 的区别',
  '进程和线程的区别',
]

const hasMoreConversations = computed(() => conversations.value.length < conversationTotal.value)

onMounted(() => {
  fetchConversations(true)
})

const { refresh: refreshConversations } = useAutoRefresh(fetchConversations, 10000)

async function refreshActiveMessages() {
  if (activeConvId.value && !streaming.value && !sendingMessage.value) {
    const res = await getMessages(activeConvId.value)
    if (res.code === 200) {
      const serverMsgs = res.data.messages || res.data
      if (serverMsgs.length !== messages.value.length) {
        messages.value = serverMsgs
        scrollToBottom()
        scheduleMermaid()
      }
    }
  }
}

const { refresh: autoRefreshMessages } = useAutoRefresh(refreshActiveMessages, 8000)

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function mergeConversations(items, replace = false) {
  const merged = replace ? [] : [...conversations.value]
  const positions = new Map(merged.map((item, index) => [item.id, index]))
  for (const item of items) {
    if (positions.has(item.id)) {
      merged[positions.get(item.id)] = item
    } else {
      positions.set(item.id, merged.length)
      merged.push(item)
    }
  }
  conversations.value = merged
}

async function fetchConversations(reset = false) {
  if (loadingConversations.value) return
  loadingConversations.value = true
  try {
    const page = reset ? 1 : 1
    const res = await getConversations({ page, size: 50 })
    if (res.code === 200) {
      mergeConversations(res.data.items || res.data, reset)
      conversationPage.value = Math.max(conversationPage.value, page)
      conversationTotal.value = res.data.total ?? conversations.value.length
    }
  } finally {
    loadingConversations.value = false
  }
}

async function loadMoreConversations() {
  if (loadingConversations.value || !hasMoreConversations.value) return
  loadingConversations.value = true
  try {
    const page = conversationPage.value + 1
    const res = await getConversations({ page, size: 50 })
    if (res.code === 200) {
      mergeConversations(res.data.items || res.data)
      conversationPage.value = page
      conversationTotal.value = res.data.total ?? conversations.value.length
    }
  } finally {
    loadingConversations.value = false
  }
}

function handleConversationScroll(event) {
  const el = event.currentTarget
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 24) loadMoreConversations()
}

async function switchConversation(id) {
  if (loadingMessages.value || id === activeConvId.value) return
  activeConvId.value = id
  const conv = conversations.value.find(c => c.id === id)
  activeConvSubjectId.value = conv?.subject_id || null
  loadingMessages.value = true
  try {
    const res = await getMessages(id)
    if (res.code === 200 && activeConvId.value === id) {
      messages.value = res.data.messages || res.data
      scheduleMermaid()
    }
  } finally {
    loadingMessages.value = false
  }
  scrollToBottom()
}

async function newConversation() {
  activeConvId.value = null
  activeConvSubjectId.value = null
  messages.value = []
  question.value = ''
  fetchConversations()
}

async function sendMessage() {
  const q = question.value.trim()
  if (!q || streaming.value) return
  question.value = ''

  const userMsg = { role: 'user', content: q }
  messages.value.push(userMsg)

  function removeOptimisticUserMessage() {
    const index = messages.value.indexOf(userMsg)
    if (index !== -1) messages.value.splice(index, 1)
  }

  streaming.value = true
  streamContent.value = ''

  const token = localStorage.getItem('access_token')
  const url = askQuestion()
  let fullContent = ''

  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question: q, conversation_id: activeConvId.value, subject_id: activeConvSubjectId.value }),
    })
    if (!resp.ok) {
      removeOptimisticUserMessage()
      const errData = await resp.json().catch(() => ({ detail: resp.statusText }))
      let msg = '请求失败: ' + (errData.detail || resp.statusText)
      if (resp.status === 422 && errData.detail) {
        const fieldErrors = errData.detail.map?.(e => `${e.loc?.slice?.(1)?.join('.') || 'question'}: ${e.msg}`).join('; ')
        msg = fieldErrors || msg
      }
      ElMessage.error(msg)
      streaming.value = false
      return
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    let streamDone = false
    let assistantSaved = false
    let resultConvId = activeConvId.value
    let resultSubjectId = activeConvSubjectId.value
    sendingMessage.value = true
    while (true) {
      const { done, value } = await reader.read()
      // Process the chunk even when done is true — the last chunk may
      // contain the "done" SSE event alongside the stream-end signal.
      if (value) {
        buffer += decoder.decode(value, { stream: true })
      }
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (data === '[DONE]') {
            streamDone = true
            break
          }
          try {
            const parsed = JSON.parse(data)
            if (parsed.type === 'token') {
              fullContent += parsed.content
              streamContent.value = fullContent
              scrollToBottom()
            } else if (parsed.type === 'done') {
              resultConvId = parsed.conversation_id
              resultSubjectId = parsed.subject_id || resultSubjectId
              activeConvId.value = resultConvId
              if (resultSubjectId) activeConvSubjectId.value = resultSubjectId
              if (fullContent) {
                messages.value.push({
                  role: 'assistant',
                  content: fullContent,
                  id: parsed.message_id,
                  sources: parsed.sources || [],
                  question_type: parsed.question_type || null,
                })
                streamContent.value = ''
                assistantSaved = true
              }
            } else if (parsed.type === 'error') {
              ElMessage.error(parsed.content)
            }
          } catch {}
        }
      }
      if (done || streamDone) break
    }
    streaming.value = false

    // If we got partial content but no done event, save what we have
    if (fullContent && !assistantSaved) {
      messages.value.push({ role: 'assistant', content: fullContent })
      streamContent.value = ''
    }

    // Refresh from server to get proper IDs and sources
    if (resultConvId) {
      refreshAfterAnswer(resultConvId)
    } else if (activeConvId.value) {
      refreshAfterAnswer(activeConvId.value)
    } else {
      fetchConversations()
    }
  } catch (e) {
    if (!assistantSaved) {
      removeOptimisticUserMessage()
    }
    ElMessage.error('请求失败：' + e.message)
    streaming.value = false
    // Try to refresh messages on network error too
    if (activeConvId.value) {
      try {
        const res = await getMessages(activeConvId.value)
        if (res.code === 200) {
          messages.value = res.data.messages || res.data
        }
      } catch {}
    }
  } finally {
    sendingMessage.value = false
  }
  await nextTick()
  scrollToBottom()
  scheduleMermaid()
}

async function handleFeedback(msgId, score) {
  try {
    feedbackMap.value[msgId] = score
    if (score <= 2 && auth.isUser) {
      const idx = messages.value.findIndex(m => m.id === msgId)
      const msg = messages.value[idx]
      const prevMsg = idx > 0 ? messages.value[idx - 1] : null
      if (msg && prevMsg) {
        await createWrongQuestion({
          subject_id: activeConvSubjectId.value || 1,
          question_content: prevMsg.content || '',
          correct_answer: msg.content || '',
          difficulty: 3,
          message_id: msgId,
        })
        ElMessage.success('已加入错题本')
      }
      await submitFeedback(msgId, score)
    } else {
      await submitFeedback(msgId, score)
      ElMessage.success('感谢反馈')
    }
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail?.message || e.message))
  }
}

async function refreshAfterAnswer(convId) {
  // Refresh conversation list and messages from server to get proper IDs/metadata
  await fetchConversations()
  if (convId) {
    const res = await getMessages(convId)
    if (res.code === 200) {
      messages.value = res.data.messages || res.data
    }
  }
  await nextTick()
  scrollToBottom()
  scheduleMermaid()
}

async function addToWrongBook(msg, idx) {
  if (!auth.isUser) return
  try {
    const prevMsg = idx > 0 ? messages.value[idx - 1] : null
    await createWrongQuestion({
      subject_id: activeConvSubjectId.value || 1,
      question_content: prevMsg?.content || '',
      correct_answer: msg.content || '',
      difficulty: 3,
      message_id: msg.id,
    })
    ElMessage.success('已加入错题本')
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail?.message || e.message))
  }
}

function scheduleMermaid() {
  nextTick(() => initializeMermaid(messagesRef.value))
}

function getNoteSources(sources) {
  if (!sources || !Array.isArray(sources)) return []
  return sources.filter(s => s.type === 'note')
}

function getOwnNoteSources(sources) {
  if (!auth.user) return []
  return getNoteSources(sources).filter(s => s.user_id === auth.user.id)
}

function getOtherNoteSources(sources) {
  if (!auth.user) return getNoteSources(sources)
  return getNoteSources(sources).filter(s => s.user_id !== auth.user.id)
}

function noteStatusTagType(status) {
  if (status === 'published') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

function noteStatusLabel(status) {
  if (status === 'published') return '已通过'
  if (status === 'rejected') return '未通过'
  return '审核中'
}
</script>

<style scoped>
.welcome h2 { font-size: 22px; color: var(--text); font-weight: 700; }
.dot-pulse::after {
  display: inline-block;
  content: '';
  animation: pulse 1.4s infinite;
  letter-spacing: 2px;
}
@keyframes pulse {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}
.markdown-body { line-height: 1.7; font-size: 14px; white-space: normal; }
.markdown-body :deep(h1) { font-size: 18px; margin: 8px 0; }
.markdown-body :deep(h2) { font-size: 16px; margin: 6px 0; }
.markdown-body :deep(h3) { font-size: 14px; margin: 4px 0; }
.markdown-body :deep(code) { background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
.markdown-body :deep(pre) { background: rgba(0,0,0,0.3); padding: 14px; border-radius: 8px; overflow-x: auto; margin: 8px 0; border: 1px solid var(--border); }
.markdown-body :deep(pre code) { background: transparent; padding: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 20px; margin: 4px 0; }
.markdown-body :deep(li) { margin: 2px 0; }

/* ── Table styles ── */
.markdown-body :deep(.table-wrapper) {
  overflow-x: auto;
  margin: 12px 0;
  border-radius: 8px;
  border: 1px solid var(--border);
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid rgba(148,163,184,0.45);
}
.markdown-body :deep(thead) {
  background: linear-gradient(135deg, rgba(124,58,237,0.15), rgba(99,102,241,0.1));
}
.markdown-body :deep(thead th) {
  padding: 10px 14px;
  text-align: center;
  font-weight: 600;
  color: var(--text);
  border: 1px solid rgba(148,163,184,0.55);
  white-space: nowrap;
}
.markdown-body :deep(tbody td) {
  padding: 8px 14px;
  text-align: center;
  color: var(--text2);
  border: 1px solid rgba(148,163,184,0.35);
}
.markdown-body :deep(tbody tr:hover) {
  background: rgba(124,58,237,0.06);
}
.markdown-body :deep(tbody tr:last-child td) {
  border-bottom: none;
}

/* ── Mermaid diagram styles ── */
.markdown-body :deep(.mermaid) {
  margin: 12px 0;
  padding: 16px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow-x: auto;
}

/* ── LaTeX math styles ── */
.markdown-body :deep(.katex-display) {
  margin: 12px 0;
  overflow-x: auto;
}
.markdown-body :deep(.katex) {
  font-size: 1.1em;
}
.feedback { margin-top: 10px; display: flex; gap: 6px; }
.feedback button { background: rgba(255,255,255,0.06); border: 1px solid var(--border); border-radius: 6px; padding: 4px 10px; font-size: 11px; cursor: pointer; color: var(--text2); transition: all 0.2s; }
.feedback button:hover { border-color: var(--primary); color: var(--primary); background: rgba(124,58,237,0.1); }
.wrong-btn { border-color: var(--warning) !important; color: var(--warning) !important; }
.wrong-btn:hover { border-color: #d97706 !important; color: #d97706 !important; background: rgba(245,158,11,0.1) !important; }

.msg-sources { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border); }
.sources-title { font-size: 12px; font-weight: 600; color: var(--text2); margin-bottom: 8px; }
.source-group { margin-bottom: 8px; }
.source-group-title { font-size: 11px; font-weight: 600; color: var(--text3); margin-bottom: 4px; }
.source-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: rgba(255,255,255,0.04); border-radius: 6px; margin-bottom: 4px; font-size: 12px; }
.source-item .source-name { color: var(--text); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-item .source-author { color: var(--text3); font-size: 11px; }
.source-item .reject-reason { color: var(--danger); font-size: 11px; }
.source-item.own-note { border-left: 3px solid var(--primary); }
.chat-list-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; border-bottom: 1px solid var(--border);
  font-size: 14px; font-weight: 600; color: var(--text);
}
.chat-item {
  padding: 12px 16px; cursor: pointer; transition: background 0.2s;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.chat-item:hover { background: rgba(124,58,237,0.08); }
.chat-item.active {
  background: rgba(124,58,237,0.15);
  border-left: 3px solid var(--primary);
  padding-left: 13px;
}
.chat-item .title {
  font-size: 14px; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.chat-item .sub {
  font-size: 12px; color: var(--text3); margin-top: 4px;
}
.chat-list-status {
  padding: 12px 16px;
  text-align: center;
  color: var(--text3);
  font-size: 12px;
}

.msg-enter-active {
  transition: all 0.35s ease-out;
}
.msg-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
</style>
