<template>
  <div>
    <div class="stat-grid">
      <div v-for="s in stats" :key="s.label" class="stat-card" :class="s.color">
        <div class="stat-glow" :style="{ background: s.glowColor }"></div>
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">{{ s.value }}</div>
        <div class="stat-desc">{{ s.desc }}</div>
        <div class="stat-icon" v-html="s.icon"></div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div class="card">
        <div class="card-header"><h3>📊 科目分布</h3><span style="font-size:11px;color:var(--text3)">文档占比</span></div>
        <div class="card-body">
          <div style="display:flex;flex-direction:column;gap:14px">
            <div v-for="s in subjectStats" :key="s.name">
              <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px">
                <span style="color:var(--text)">{{ s.name }}</span>
                <span style="color:var(--text2)">{{ s.pct }}%</span>
              </div>
              <div class="progress-bar"><div class="fill" :style="{ width: s.pct + '%' }"></div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3>🔥 系统运行状态</h3></div>
        <div class="card-body" style="display:flex;flex-direction:column;gap:14px">
          <div v-for="s in services" :key="s.name" style="display:flex;align-items:center;gap:8px">
            <span class="status-dot green"></span>
            <span style="font-size:13px">{{ s.name }}</span>
            <span style="font-size:11px;color:var(--text3)">{{ s.status }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:20px">
      <div class="card-header"><h3>📈 近7日对话趋势</h3></div>
      <div class="card-body">
        <div ref="trendChartRef" style="height:260px"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import request from '@/api/request'

const trendChartRef = ref(null)
let trendChart = null

const stats = ref([
  { label: '知识库文档', value: '—', desc: '加载中...', color: 'blue', glowColor: '#818cf8', icon: '&#128218;' },
  { label: '知识点总数', value: '—', desc: '提取自语料', color: 'purple', glowColor: '#7c3aed', icon: '&#129504;' },
  { label: '注册用户', value: '—', desc: '加载中...', color: 'cyan', glowColor: '#06b6d4', icon: '&#128101;' },
  { label: '问答次数', value: '—', desc: '加载中...', color: 'green', glowColor: '#10b981', icon: '&#128172;' },
  { label: '学习心得', value: '—', desc: '加载中...', color: 'pink', glowColor: '#f472b6', icon: '&#128214;' },
])

const subjectStats = ref([])
const services = ref([
  { name: 'ChromaDB', status: '正常' },
  { name: 'Neo4j', status: '正常' },
  { name: 'MySQL', status: '正常' },
  { name: 'Redis', status: '正常' },
  { name: '大模型 API', status: '正常' },
  { name: '文档解析引擎', status: '正常' },
])

onMounted(async () => {
  try {
    const res = await request.get('/admin/dashboard')
    if (res.code === 200) {
      const d = res.data
      stats.value = [
        { label: '知识库文档', value: d.total_documents, desc: '已解析上线', color: 'blue', glowColor: '#818cf8', icon: '&#128218;' },
        { label: '知识点总数', value: d.total_knowledge_points, desc: '提取自语料', color: 'purple', glowColor: '#7c3aed', icon: '&#129504;' },
        { label: '注册用户', value: d.total_users, desc: '系统用户', color: 'cyan', glowColor: '#06b6d4', icon: '&#128101;' },
        { label: '问答次数', value: d.total_conversations, desc: '累计对话', color: 'green', glowColor: '#10b981', icon: '&#128172;' },
        { label: '学习心得', value: d.total_notes, desc: '已发布', color: 'pink', glowColor: '#f472b6', icon: '&#128214;' },
      ]

      const total = d.docs_by_subject.reduce((s, x) => s + x.count, 0) || 1
      subjectStats.value = d.docs_by_subject.map(s => ({
        name: s.name || '未知',
        pct: Math.round((s.count / total) * 100),
      }))

      if (d.recent_conversations?.length) {
        trendChart = echarts.init(trendChartRef.value)
        trendChart.setOption({
          tooltip: { trigger: 'axis', theme: 'dark' },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'category', data: d.recent_conversations.map(r => r.date.slice(5)), axisLabel: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#2d2d4e' } } },
          yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#2d2d4e' } } },
          series: [{
            type: 'line', data: d.recent_conversations.map(r => r.count),
            smooth: true, areaStyle: { color: 'rgba(124,58,237,0.15)' },
            lineStyle: { color: '#7c3aed' }, itemStyle: { color: '#7c3aed' },
          }],
        })
      }
    }
  } catch {
    ElMessage.error('获取统计数据失败')
  }
})

onBeforeUnmount(() => {
  trendChart?.dispose()
})
</script>

<style scoped>
</style>
