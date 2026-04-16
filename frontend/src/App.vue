<template>
  <div class="app">
    <header class="header">
      <div class="header-inner">
        <div class="logo" @click="resetSearch">
          <span class="logo-icon">🎓</span>
          <span>校园智能问答</span>
        </div>
        <div class="header-stats" v-if="stats">
          已索引 {{ stats.total_documents }} 篇文档 · {{ stats.chroma_chunks }} 个分块
        </div>
      </div>
    </header>

    <!-- 搜索首页 -->
    <div v-if="!hasSearched" class="hero">
      <h1>校园知识，一问即答</h1>
      <p>基于学校官网内容的智能检索问答系统，支持来源溯源</p>
      <SearchBox
        v-model="query"
        :loading="loading"
        @search="doSearch"
      />
      <div class="suggestions">
        <span
          v-for="s in suggestions"
          :key="s"
          class="suggest-tag"
          @click="query = s; doSearch()"
        >{{ s }}</span>
      </div>
    </div>

    <!-- 搜索结果页 -->
    <div v-else class="main-content">
      <SearchBox
        v-model="query"
        :loading="loading"
        @search="doSearch"
      />

      <!-- 加载中 -->
      <div v-if="loading" style="text-align: center; padding: 40px 0;">
        <div class="loading-spinner"></div>
        <p style="margin-top: 12px; color: var(--text-secondary);">
          {{ useLlm ? '正在检索并生成回答...' : '正在检索...' }}
        </p>
        <div v-if="useLlm" class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>

      <!-- 错误 -->
      <div v-else-if="error" class="answer-card" style="border-left-color: var(--error);">
        <p style="color: var(--error);">{{ error }}</p>
      </div>

      <!-- 结果 -->
      <template v-else-if="response">
        <!-- AI回答 -->
        <div v-if="response.answer" class="answer-card">
          <h3>
            <span v-if="response.has_llm">🤖 AI 回答</span>
            <span v-else>📋 检索结果</span>
          </h3>
          <div class="answer-content" v-html="renderedAnswer"></div>
        </div>

        <!-- 来源链接 -->
        <div v-if="response.sources && response.sources.length" class="sources-section">
          <h4>📎 相关链接</h4>
          <div v-for="(s, i) in response.sources" :key="i" class="source-link">
            <span class="site-badge">{{ s.site || '来源' }}</span>
            <a :href="s.url" target="_blank" rel="noopener">{{ s.title || s.url }}</a>
          </div>
        </div>

        <!-- 状态栏 -->
        <div class="status-bar">
          <div class="time-info">
            <span v-if="response.retrieve_time_ms">检索: {{ response.retrieve_time_ms }}ms</span>
            <span v-if="response.generate_time_ms">生成: {{ response.generate_time_ms }}ms</span>
            <span>总耗时: {{ response.total_time_ms }}ms</span>
          </div>
          <span :class="['status-badge', response.has_llm ? 'llm' : 'fallback']">
            {{ response.has_llm ? 'AI摘要' : '纯检索' }}
          </span>
        </div>

        <!-- 详细结果 -->
        <details style="margin-top: 16px;">
          <summary style="cursor: pointer; color: var(--text-secondary); font-size: 14px;">
            查看检索详情 ({{ response.results.length }} 条)
          </summary>
          <ResultItem
            v-for="(r, i) in response.results"
            :key="i"
            :result="r"
          />
        </details>
      </template>
    </div>

    <footer class="footer">
      校园智能问答系统 · 基于RAG技术 · 来源可溯源
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import MarkdownIt from 'markdown-it'
import SearchBox from './components/SearchBox.vue'
import ResultItem from './components/ResultItem.vue'
import { search, getStats } from './api'
import type { SearchResponse, StatsResponse } from './api/types'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
})

const query = ref('')
const loading = ref(false)
const hasSearched = ref(false)
const error = ref('')
const response = ref<SearchResponse | null>(null)
const stats = ref<StatsResponse | null>(null)
const useLlm = ref(true)

const suggestions = [
  '选课流程',
  '奖学金申请条件',
  '保研政策',
  '图书馆开放时间',
  '转专业流程',
  '毕业学分要求',
]

const renderedAnswer = computed(() => {
  if (!response.value?.answer) return ''
  return md.render(response.value.answer)
})

function resetSearch() {
  hasSearched.value = false
  response.value = null
  error.value = ''
  query.value = ''
}

async function doSearch() {
  const q = query.value.trim()
  if (!q || loading.value) return

  loading.value = true
  error.value = ''
  hasSearched.value = true
  response.value = null

  try {
    console.log('[App] Sending search request:', { query: q, useLlm: useLlm.value })
    response.value = await search({
      query: q,
      top_k: 8,
      use_llm: useLlm.value,
    })
    console.log('[App] Got response:', response.value)

    if (response.value.error) {
      error.value = response.value.error
    }
  } catch (e: any) {
    console.error('[App] Search error details:', e)
    // Extract detailed error info
    const detail = e?.response?.data?.detail || e?.response?.data
    const status = e?.response?.status
    const code = e?.code
    const msg = e?.message
    
    if (status) {
      error.value = `服务器错误 (${status}): ${detail || msg}`
    } else if (code === 'ERR_NETWORK' || code === 'ECONNREFUSED' || msg?.includes('Network')) {
      error.value = '网络错误: 无法连接到API服务。请确保后端服务(端口8000)正在运行。'
    } else {
      error.value = `请求失败: ${msg || String(e)}`
    }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    stats.value = await getStats()
  } catch {
    // ignore
  }
})
</script>
