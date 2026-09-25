import type { Answer, Comparison, DocSummary, Document, HistoryItem, IndexProgress, Prep, SummaryAnswer } from './types'

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), 'X-Requested-With': 'Plainclause', ...init.headers },
    credentials: 'same-origin',
  })
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`
    try { const data = await response.json(); if (typeof data.detail === 'string') detail = data.detail } catch { /* keep safe generic error */ }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export const api = {
  status: () => request<{ model_available: boolean; disclaimer: string; hosted_preview: boolean; hosted_service: boolean }>('/status'),
  list: () => request<DocSummary[]>('/documents'),
  document: (id: string) => request<Document>(`/documents/${id}`),
  indexStatus: (id: string) => request<IndexProgress>(`/documents/${id}/index`),
  indexBatch: (id: string, offset: number) => request<IndexProgress>(`/documents/${id}/index?offset=${offset}`, { method: 'POST' }),
  history: (id: string) => request<HistoryItem[]>(`/documents/${id}/history`),
  deleteDocument: (id: string) => request<{ deleted: boolean }>(`/documents/${id}`, { method: 'DELETE' }),
  deleteAll: () => request<{ deleted_documents: number }>('/data', { method: 'DELETE' }),
  ask: (document_id: string, question: string) => request<Answer>('/ask', { method: 'POST', body: JSON.stringify({ document_id, question }) }),
  summary: (id: string, offset = 0, level: 'simple' | 'detailed' = 'simple') => request<SummaryAnswer>(`/documents/${id}/summary?offset=${offset}&level=${level}`, { method: 'POST' }),
  summaries: (id: string, level: 'simple' | 'detailed' = 'simple') => request<SummaryAnswer[]>(`/documents/${id}/summaries?level=${level}`),
  clearSummaries: (id: string) => request<{ deleted: boolean }>(`/documents/${id}/summaries`, { method: 'DELETE' }),
  simplify: (id: string, chunk_id: string, level: 'simple' | 'detailed') => request<Answer>(`/documents/${id}/simplify`, { method: 'POST', body: JSON.stringify({ chunk_id, level }) }),
  compare: (document_ids: string[]) => request<Comparison>('/compare', { method: 'POST', body: JSON.stringify({ document_ids }) }),
  prepare: (id: string) => request<Prep>(`/documents/${id}/prepare`),
}

export async function askStream(document_id: string, question: string, onStatus: (value: string) => void): Promise<Answer> {
  const response = await fetch('/api/ask/stream', {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'Plainclause' },
    body: JSON.stringify({ document_id, question }),
  })
  if (!response.ok || !response.body) {
    let detail = `Request failed (${response.status}).`
    try { const data = await response.json(); if (typeof data.detail === 'string') detail = data.detail } catch { /* keep safe generic error */ }
    throw new Error(detail)
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result: Answer | null = null
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.trim()) continue
      const event = JSON.parse(line) as { type: string; message?: string; characters?: number; answer?: Answer }
      if (event.type === 'status' && event.message) onStatus(event.message)
      if (event.type === 'progress') onStatus(`Checking the AI draft against sources · ${event.characters || 0} characters received`)
      if (event.type === 'result' && event.answer) result = event.answer
    }
    if (done) break
  }
  if (!result) throw new Error('The local service ended before it could verify an answer.')
  return result
}

export function upload(file: File, onProgress: (message: string) => void): Promise<{ id: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/documents')
    xhr.withCredentials = true
    xhr.setRequestHeader('X-Requested-With', 'Plainclause')
    xhr.upload.onprogress = event => {
      if (event.lengthComputable) onProgress(`Uploading ${Math.round(event.loaded / event.total * 100)}%`)
    }
    xhr.upload.onload = () => onProgress('Extracting sections…')
    xhr.onerror = () => reject(new Error('The upload could not connect to the local service.'))
    xhr.onload = () => {
      let result: { id?: string; detail?: string }
      try { result = JSON.parse(xhr.responseText) } catch { reject(new Error('The local service returned an unreadable response.')); return }
      if (xhr.status >= 200 && xhr.status < 300 && result.id) resolve({ id: result.id })
      else reject(new Error(result.detail || `Upload failed (${xhr.status}).`))
    }
    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  })
}
