import axios from 'axios'
import type { SearchRequest, SearchResponse, StatsResponse, HealthResponse } from './types'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000, // 3分钟，LLM生成可能较慢
})

// 响应拦截器：记录详细错误
api.interceptors.response.use(
  response => {
    console.log('[API] Response:', response.config.url, response.status)
    return response
  },
  error => {
    console.error('[API] Error:', error.message)
    console.error('[API] Config:', error.config?.url, error.config?.method)
    console.error('[API] Response:', error.response?.status, error.response?.data)
    return Promise.reject(error)
  }
)

export async function search(req: SearchRequest): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>('/search', req)
  return data
}

export async function searchStream(req: SearchRequest): AsyncGenerator<string> {
  const response = await fetch('/api/search/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!response.body) throw new Error('Stream not supported')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  async function* generate() {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (data === '[DONE]') return
          try {
            const parsed = JSON.parse(data)
            if (parsed.content) yield parsed.content
            if (parsed.error) throw new Error(parsed.error)
          } catch {
            // skip invalid JSON
          }
        }
      }
    }
  }

  return generate()
}

export async function suggest(query: string, topK = 5): Promise<SearchResponse> {
  const { data } = await api.get<SearchResponse>('/suggest', {
    params: { q: query, top_k: topK },
  })
  return data
}

export async function getStats(): Promise<StatsResponse> {
  const { data } = await api.get<StatsResponse>('/stats')
  return data
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health')
  return data
}
