import type { ApiResponse, KnowledgeFile, MemoryDetail, MemoryItem, MemoryVersion } from '@/types'
import { apiUrl, authHeaders, request } from './http'

export async function listKnowledgeDocuments() {
  return request<{ files: KnowledgeFile[] }>('/knowledge/list')
}

export async function uploadKnowledgeDocument(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(apiUrl('/knowledge/upload'), { method: 'POST', body: fd, headers: authHeaders() })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json() as Promise<ApiResponse>
}

export async function deleteKnowledgeDocument(filename: string) {
  return request(`/knowledge/${encodeURIComponent(filename)}`, { method: 'DELETE' })
}

export async function listMemoryItems() {
  return request<{ items: MemoryItem[] }>('/knowledge/memory/list')
}

export async function readMemoryItem(path: string) {
  return request<{ item: MemoryDetail }>(`/knowledge/memory/read?path=${encodeURIComponent(path)}`)
}

export async function deleteMemoryItem(path: string) {
  return request(`/knowledge/memory?path=${encodeURIComponent(path)}`, { method: 'DELETE' })
}

export async function listMemoryVersions(limit = 50) {
  return request<{ versions: MemoryVersion[] }>(`/knowledge/memory/versions?limit=${limit}`)
}
