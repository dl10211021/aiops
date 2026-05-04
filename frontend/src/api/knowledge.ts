import type { ApiResponse, KnowledgeFile, MemoryDetail, MemoryItem, MemoryStoreInfo, MemoryVersion } from '@/types'
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

export async function listMemoryStores() {
  return request<{ stores: MemoryStoreInfo[] }>('/knowledge/memory/stores')
}

export async function readMemoryItem(path: string) {
  return request<{ item: MemoryDetail }>(`/knowledge/memory/read?path=${encodeURIComponent(path)}`)
}

export async function deleteMemoryItem(path: string) {
  return request(`/knowledge/memory?path=${encodeURIComponent(path)}`, { method: 'DELETE' })
}

export async function updateMemoryItem(path: string, content: string, contentSha256?: string) {
  return request<{ item: MemoryDetail }>(`/knowledge/memory?path=${encodeURIComponent(path)}`, {
    method: 'PUT',
    body: JSON.stringify({ content, content_sha256: contentSha256 }),
  })
}

export async function restoreMemoryVersion(versionId: string) {
  return request<{ version: MemoryVersion }>('/knowledge/memory/restore', {
    method: 'POST',
    body: JSON.stringify({ version_id: versionId }),
  })
}

export async function exportMemoryStore() {
  return request<{ export: Record<string, unknown> }>('/knowledge/memory/export')
}

export async function listMemoryVersions(limit = 50) {
  return request<{ versions: MemoryVersion[] }>(`/knowledge/memory/versions?limit=${limit}`)
}
