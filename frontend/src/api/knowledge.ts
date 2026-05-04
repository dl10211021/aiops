import type { ApiResponse, KnowledgeCompileQueueItem, KnowledgeFile, KnowledgeVaultSearchResult, MemoryDetail, MemoryItem, MemoryPendingConflict, MemoryReviewItem, MemorySearchResult, MemoryStoreInfo, MemoryVersion } from '@/types'
import { apiUrl, authHeaders, request } from './http'

export async function listKnowledgeDocuments() {
  return request<{ files: KnowledgeFile[] }>('/knowledge/list')
}

export async function listKnowledgeVaultQueue() {
  return request<{ items: KnowledgeCompileQueueItem[] }>('/knowledge/vault/queue')
}

export async function listKnowledgeVaultCandidates() {
  return request<{ items: KnowledgeCompileQueueItem[] }>('/knowledge/vault/candidates')
}

export async function listKnowledgeVaultArticles() {
  return request<{ items: KnowledgeCompileQueueItem[] }>('/knowledge/vault/articles')
}

export async function compileKnowledgeVaultSource(sourceSessionId: string, useAi = true) {
  return request<{ item: KnowledgeCompileQueueItem }>('/knowledge/vault/compile', {
    method: 'POST',
    body: JSON.stringify({
      source_session_id: sourceSessionId,
      use_ai: useAi,
    }),
  })
}

export async function approveKnowledgeVaultCandidate(sourceSessionId: string) {
  return request<{ item: KnowledgeCompileQueueItem }>('/knowledge/vault/approve', {
    method: 'POST',
    body: JSON.stringify({
      source_session_id: sourceSessionId,
    }),
  })
}

export async function readKnowledgeVaultCandidate(sourceSessionId: string) {
  return request<{ item: KnowledgeCompileQueueItem }>(`/knowledge/vault/candidate?source_session_id=${encodeURIComponent(sourceSessionId)}`)
}

export async function readKnowledgeVaultArticle(sourceSessionId: string) {
  return request<{ item: KnowledgeCompileQueueItem }>(`/knowledge/vault/article?source_session_id=${encodeURIComponent(sourceSessionId)}`)
}

export async function searchKnowledgeVault(query: string, scope = 'all', limit = 20) {
  return request<{ results: KnowledgeVaultSearchResult[] }>('/knowledge/vault/search', {
    method: 'POST',
    body: JSON.stringify({ query, scope, limit }),
  })
}

export async function updateKnowledgeVaultCandidate(sourceSessionId: string, content: string, contentSha256?: string) {
  return request<{ item: KnowledgeCompileQueueItem }>('/knowledge/vault/candidate', {
    method: 'PUT',
    body: JSON.stringify({
      source_session_id: sourceSessionId,
      content,
      content_sha256: contentSha256,
    }),
  })
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

export async function createMemoryItem(scopeId: string, summary: string) {
  return request<{ version: MemoryVersion }>('/knowledge/memory', {
    method: 'POST',
    body: JSON.stringify({
      scope_id: scopeId,
      summary,
      source_session_id: 'manual',
    }),
  })
}

export async function searchMemoryItems(query: string, scopeIds: string[], limit = 6) {
  return request<{ results: MemorySearchResult[] }>('/knowledge/memory/search', {
    method: 'POST',
    body: JSON.stringify({
      query,
      scope_ids: scopeIds,
      limit,
    }),
  })
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

export async function redactMemoryVersion(versionId: string) {
  return request<{ version: MemoryVersion }>('/knowledge/memory/versions/redact', {
    method: 'POST',
    body: JSON.stringify({ version_id: versionId }),
  })
}

export async function listMemoryPendingConflicts(limit = 50) {
  return request<{ items: MemoryPendingConflict[] }>(`/knowledge/memory/pending?limit=${limit}`)
}

export async function listMemoryReviewItems(staleDays = 180, limit = 50) {
  return request<{ items: MemoryReviewItem[] }>(`/knowledge/memory/review?stale_days=${staleDays}&limit=${limit}`)
}

export async function resolveMemoryPendingConflict(versionId: string, action: 'accept_new' | 'keep_old' | 'merged') {
  return request<{ version: MemoryVersion }>('/knowledge/memory/pending/resolve', {
    method: 'POST',
    body: JSON.stringify({ version_id: versionId, action }),
  })
}

export async function confirmMemoryReview(path: string) {
  return request<{ version: MemoryVersion }>('/knowledge/memory/review/confirm', {
    method: 'POST',
    body: JSON.stringify({ path }),
  })
}

export async function exportMemoryStore() {
  return request<{ export: Record<string, unknown> }>('/knowledge/memory/export')
}

export async function listMemoryVersions(limit = 50) {
  return request<{ versions: MemoryVersion[] }>(`/knowledge/memory/versions?limit=${limit}`)
}
