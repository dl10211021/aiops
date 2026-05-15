import type {
  ApiResponse,
  KnowledgeCompileQueueItem,
  KnowledgeDocumentContent,
  KnowledgeFile,
  KnowledgeListPagination,
  KnowledgeListSummary,
  KnowledgeReindexResult,
  KnowledgeVaultGraph,
  KnowledgeVaultSearchResult,
  KnowledgeVectorStoreStatus,
  LearningCandidate,
  LearningCandidatePublishedArtifactDetail,
  MemoryCandidate,
  MemoryDetail,
  MemoryItem,
  MemoryPendingConflict,
  MemoryQualityReport,
  MemoryReviewItem,
  MemorySearchResult,
  MemoryStoreInfo,
  MemoryVersion,
} from '@/types'
import { apiUrl, authHeaders, request } from './http'

export async function listKnowledgeDocuments(params?: {
  query?: string
  vectorStatus?: string
  extension?: string
  page?: number
  perPage?: number
  sort?: string
}, options?: RequestInit) {
  const search = new URLSearchParams()
  if (params?.query) search.set('q', params.query)
  if (params?.vectorStatus) search.set('vector_status', params.vectorStatus)
  if (params?.extension) search.set('extension', params.extension)
  if (params?.page) search.set('page', String(params.page))
  if (params?.perPage) search.set('per_page', String(params.perPage))
  if (params?.sort) search.set('sort', params.sort)
  const suffix = search.toString() ? `?${search.toString()}` : ''
  return request<{
    files: KnowledgeFile[]
    summary?: KnowledgeListSummary
    pagination?: KnowledgeListPagination
    vector_store?: KnowledgeVectorStoreStatus
  }>(`/knowledge/list${suffix}`, options)
}

export async function readKnowledgeDocument(filename: string) {
  return request<{ item: KnowledgeDocumentContent }>(`/knowledge/document?filename=${encodeURIComponent(filename)}`)
}

export async function reindexKnowledgeDocument(filename: string) {
  return request<{ item: KnowledgeReindexResult }>('/knowledge/document/reindex', {
    method: 'POST',
    body: JSON.stringify({ filename }),
  })
}

export async function listKnowledgeVaultQueue(options?: RequestInit) {
  return request<{ items: KnowledgeCompileQueueItem[] }>('/knowledge/vault/queue', options)
}

export async function listKnowledgeVaultCandidates(options?: RequestInit) {
  return request<{ items: KnowledgeCompileQueueItem[] }>('/knowledge/vault/candidates', options)
}

export async function listKnowledgeVaultArticles(options?: RequestInit) {
  return request<{ items: KnowledgeCompileQueueItem[] }>('/knowledge/vault/articles', options)
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

export async function graphKnowledgeVault(includeCandidates = true) {
  return request<KnowledgeVaultGraph>('/knowledge/vault/graph', {
    method: 'POST',
    body: JSON.stringify({ include_candidates: includeCandidates }),
  })
}

export async function exportKnowledgeVault() {
  const res = await fetch(apiUrl('/knowledge/vault/export'), { headers: authHeaders() })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.blob()
}

export async function importKnowledgeVault(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(apiUrl('/knowledge/vault/import'), { method: 'POST', body: fd, headers: authHeaders() })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json() as Promise<ApiResponse>
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

export async function listMemoryItems(options?: RequestInit) {
  return request<{ items: MemoryItem[] }>('/knowledge/memory/list', options)
}

export async function listMemoryStores(options?: RequestInit) {
  return request<{ stores: MemoryStoreInfo[] }>('/knowledge/memory/stores', options)
}

export async function readMemoryItem(path: string) {
  return request<{ item: MemoryDetail }>(`/knowledge/memory/read?path=${encodeURIComponent(path)}`)
}

export async function createMemoryItem(scopeId: string, summary: string, sourceSessionId = 'manual') {
  return request<{ version: MemoryVersion }>('/knowledge/memory', {
    method: 'POST',
    body: JSON.stringify({
      scope_id: scopeId,
      summary,
      source_session_id: sourceSessionId,
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

export async function listMemoryPendingConflicts(limit = 50, options?: RequestInit) {
  return request<{ items: MemoryPendingConflict[] }>(`/knowledge/memory/pending?limit=${limit}`, options)
}

export async function listMemoryCandidates(limit = 50, statuses = ['pending'], options?: RequestInit) {
  const search = new URLSearchParams()
  search.set('limit', String(limit))
  search.set('statuses', statuses.join(','))
  return request<{ items: MemoryCandidate[] }>(`/knowledge/memory/candidates?${search.toString()}`, options)
}

export async function listMemoryLearningCandidates(limit = 50, targetType = '', options?: RequestInit) {
  const search = new URLSearchParams()
  search.set('limit', String(limit))
  if (targetType) search.set('target_type', targetType)
  return request<{ items: LearningCandidate[] }>(`/knowledge/memory/learning-candidates?${search.toString()}`, options)
}

export type LearningCandidateStatus = 'draft' | 'reviewing' | 'approved' | 'rejected' | 'published'

export async function updateMemoryLearningCandidateStatus(
  candidateId: string,
  status: LearningCandidateStatus,
  reason: string,
  actor = 'user',
) {
  return request<{ item: LearningCandidate }>(
    `/knowledge/memory/learning-candidates/${encodeURIComponent(candidateId)}/status`,
    {
      method: 'PATCH',
      body: JSON.stringify({ status, reason, actor }),
    },
  )
}

export async function readLearningCandidatePublishArtifact(candidateId: string) {
  return request<{ artifact: LearningCandidatePublishedArtifactDetail }>(
    `/knowledge/memory/learning-candidates/${encodeURIComponent(candidateId)}/artifact`,
  )
}

export async function downloadLearningCandidatePublishArtifact(candidateId: string) {
  const res = await fetch(
    apiUrl(`/knowledge/memory/learning-candidates/${encodeURIComponent(candidateId)}/artifact?download=true`),
    { headers: authHeaders() },
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err && typeof err === 'object' && (err as { detail?: string }).detail) || res.statusText)
  }
  const cd = res.headers.get('content-disposition') || ''
  const filenameMatch = cd.match(/filename="?([^"]+)"?/)
  const filename = filenameMatch ? filenameMatch[1] : `${candidateId}.md`
  const blob = await res.blob()
  return { blob, filename }
}

export async function updateMemoryLearningCandidateQualityChecklist(
  candidateId: string,
  checklist: NonNullable<LearningCandidate['quality_checklist']>,
  reason: string,
  actor = 'user',
) {
  return request<{ item: LearningCandidate }>(
    `/knowledge/memory/learning-candidates/${encodeURIComponent(candidateId)}/quality-checklist`,
    {
      method: 'PATCH',
      body: JSON.stringify({ checklist, reason, actor }),
    },
  )
}

export type MemoryCandidateAction = 'confirm' | 'reject' | 'to_runbook' | 'to_skill'

export async function resolveMemoryCandidate(candidateId: string, action: MemoryCandidateAction) {
  return request<{ version: MemoryVersion }>('/knowledge/memory/candidates/resolve', {
    method: 'POST',
    body: JSON.stringify({ candidate_id: candidateId, action }),
  })
}

export async function listMemoryReviewItems(staleDays = 180, limit = 50, options?: RequestInit) {
  return request<{ items: MemoryReviewItem[] }>(`/knowledge/memory/review?stale_days=${staleDays}&limit=${limit}`, options)
}

export async function getMemoryQuality(staleDays = 180, limit = 8, options?: RequestInit) {
  return request<{ quality: MemoryQualityReport }>(`/knowledge/memory/quality?stale_days=${staleDays}&limit=${limit}`, options)
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

export async function listMemoryVersions(limit = 50, options?: RequestInit) {
  return request<{ versions: MemoryVersion[] }>(`/knowledge/memory/versions?limit=${limit}`, options)
}
