import { useState, type ChangeEvent } from 'react'
import type { LearningCandidateStatus, MemoryCandidateAction } from '@/api/knowledge'
import type {
  ExecTraceItem,
  KnowledgeCompileQueueItem,
  KnowledgeDocumentContent,
  KnowledgeFile,
  KnowledgeListPagination,
  KnowledgeListSummary,
  KnowledgeVaultGraph,
  KnowledgeVaultSearchResult,
  KnowledgeVectorStoreStatus,
  LearningCandidate,
  LearningCandidatePublishedArtifactDetail,
  MemoryCandidate,
  MemoryCandidateRef,
  MemoryDetail,
  MemoryItem,
  MemoryPendingConflict,
  MemoryQualityReport,
  MemoryReviewItem,
  MemorySearchResult,
  MemoryStoreInfo,
  MemoryVersion,
  SessionMemoryActivity,
} from '@/types'
import ToolTraceList from '@/features/sessions/ToolTraceList'
import { ACCEPTED_KNOWLEDGE_TYPES, knowledgeFileKind } from './knowledgeBaseModel'

export type KnowledgeTab = 'documents' | 'memory'

function knowledgeStatusLabel(file: KnowledgeFile) {
  if (file.compile_status === 'pending_ai_compile') return '已进入 RAG 库'
  if (file.compile_status === 'approved') return 'RAG 资料'
  if (file.compile_status === 'awaiting_review') return '待归档资料'
  if (file.compile_status === 'candidate_generated') return 'AI 摘要'
  if (file.compile_status === 'analysis_ready') return '已分析资料'
  if (file.compile_status) return file.compile_status
  if (file.status === 'legacy_vector') return '旧版 RAG 资料'
  return file.status || '已保存'
}

function vectorStatusLabel(file: KnowledgeFile) {
  if (file.vector_status === 'indexed') return 'RAG 已就绪'
  if (file.vector_status === 'skipped') return '仅原文可查'
  if (file.vector_status === 'failed') return 'RAG 索引未完成'
  if (file.vector_status === 'pending') return '正在建立 RAG 索引'
  return file.chunks !== undefined ? `RAG 切片 ${file.chunks} 段` : '原文已保存'
}

function ragErrorHint(message?: string) {
  if (!message) return ''
  const lower = message.toLowerCase()
  if (lower.includes('model not found') || lower.includes('404')) {
    return 'Embedding 模型不存在或未配置。资料已经保存，可先用原文和关键词检索；配置可用 Embedding 模型后再重建 RAG 索引。'
  }
  if (lower.includes('timeout') || lower.includes('timed out')) {
    return 'Embedding 请求超时。资料已经保存，可稍后刷新或重建 RAG 索引。'
  }
  return message
}

function ragKindLabel(label?: string) {
  const text = String(label || '证据')
  return text
    .replace(/正式\s*Wiki|Wiki\s*知识|正式知识/g, 'RAG 资料')
    .replace(/候选\s*Wiki|Wiki\s*草稿|候选草稿/g, 'AI 摘要')
    .replace(/Source\s*卡片|source\s*session/gi, '来源记录')
}

function ragDisplayPath(path?: string) {
  const text = String(path || '')
  return text
    .replace(/^wiki\/articles\//, 'RAG资料/')
    .replace(/^wiki\/candidates\//, 'AI摘要/')
    .replace(/^wiki\/sources\//, '来源记录/')
    .replace(/^raw\/uploads\//, '原文/')
}

function candidateEvidenceActionText(ref: MemoryCandidateRef) {
  return ref.command_action || ref.sql_action || ref.http_action || ref.action_label || ''
}

function formatMemorySize(size: number) {
  if (!Number.isFinite(size) || size <= 0) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KiB`
  return `${(size / 1024 / 1024).toFixed(1)} MiB`
}

function memoryKindLabel(kind?: string, fallback?: string) {
  const key = String(kind || '').trim()
  const labels: Record<string, string> = {
    session_state: '会话状态',
    success_experience: '成功经验',
    error_feedback: '错误反馈',
    asset_profile: '资产画像',
    user_preference: '用户偏好',
    platform_rule: '平台规则',
    audit_archive: '审计归档',
    session_trajectory: '会话轨迹',
  }
  return labels[key] || fallback || key || '会话状态'
}

function memoryKindTone(kind?: string) {
  const key = String(kind || '').trim()
  if (key === 'success_experience') return 'border-ops-success/35 bg-ops-success/10 text-ops-success'
  if (key === 'error_feedback') return 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert'
  if (key === 'audit_archive' || key === 'session_trajectory') return 'border-amber-300/35 bg-amber-300/10 text-amber-200'
  if (key === 'asset_profile') return 'border-ops-accent/35 bg-ops-accent/10 text-ops-accent'
  return 'border-ops-surface1 bg-ops-dark/30 text-ops-subtext'
}

function memoryUsageLabel(item: Pick<MemoryItem, 'retrieval_enabled' | 'retrieval_entries' | 'audit_entries'>) {
  if (item.retrieval_enabled === false) return '仅审计，不进上下文'
  const retrieval = item.retrieval_entries ?? 0
  const audit = item.audit_entries ?? 0
  if (retrieval > 0 && audit > 0) return `可召回 ${retrieval} 条 / 审计 ${audit} 条`
  if (retrieval > 0) return `会进入上下文 ${retrieval} 条`
  if (audit > 0) return `仅审计 ${audit} 条`
  return '等待分类'
}

function dominantMemoryKind(item: MemoryItem) {
  const kinds = item.entry_kinds || {}
  const ranked = Object.entries(kinds).sort((a, b) => b[1] - a[1])
  return ranked[0]?.[0] || (item.archived ? 'audit_archive' : 'session_state')
}

function memoryKindChips(item: MemoryItem) {
  const kinds = item.entry_kinds || {}
  const entries = Object.entries(kinds).sort((a, b) => b[1] - a[1])
  if (!entries.length) {
    const kind = dominantMemoryKind(item)
    return [{ kind, label: memoryKindLabel(kind), count: item.entries || 0 }]
  }
  return entries.map(([kind, count]) => ({ kind, label: memoryKindLabel(kind), count }))
}

export function KnowledgeTabs({
  activeTab,
  documentCount,
  memoryCount,
  onChange,
}: {
  activeTab: KnowledgeTab
  documentCount: number
  memoryCount: number
  onChange: (tab: KnowledgeTab) => void
}) {
  const tabs: Array<[KnowledgeTab, string, string]> = [
    ['documents', '资料库', `${documentCount} 个资料`],
    ['memory', 'AI 记忆', `${memoryCount} 条记忆`],
  ]
  return (
    <div className="mb-4 flex flex-wrap gap-2 rounded-xl border border-ops-surface0 bg-ops-panel/55 p-1">
      {tabs.map(([id, label, desc]) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`rounded-lg px-4 py-2 text-left transition-colors ${
            activeTab === id
              ? 'bg-ops-accent text-ops-dark'
              : 'text-ops-subtext hover:bg-ops-surface0/70 hover:text-ops-text'
          }`}
        >
          <span className="block text-sm font-semibold">{label}</span>
          <span className="block text-[11px] opacity-80">{desc}</span>
        </button>
      ))}
    </div>
  )
}

interface UploadInputProps {
  disabled: boolean
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void
}

function UploadInput({ disabled, onUpload }: UploadInputProps) {
  return (
    <input
      type="file"
      multiple
      accept={ACCEPTED_KNOWLEDGE_TYPES}
      onChange={onUpload}
      className="hidden"
      disabled={disabled}
    />
  )
}

export function KnowledgeUploadButton({
  uploading,
  onUpload,
}: {
  uploading: boolean
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void
}) {
  return (
    <label className="ops-primary-action cursor-pointer px-3 py-1.5 text-sm">
      {uploading ? '上传中...' : '上传资料'}
      <UploadInput disabled={uploading} onUpload={onUpload} />
    </label>
  )
}

export function KnowledgeLibraryControls({
  extension,
  pageSize,
  pagination,
  query,
  sort,
  summary,
  vectorStatus,
  vectorStore,
  onExtensionChange,
  onPageChange,
  onPageSizeChange,
  onQueryChange,
  onRefresh,
  onSortChange,
  onVectorStatusChange,
}: {
  extension: string
  pageSize: number
  pagination: KnowledgeListPagination | null
  query: string
  sort: string
  summary: KnowledgeListSummary | null
  vectorStatus: string
  vectorStore: KnowledgeVectorStoreStatus | null
  onExtensionChange: (value: string) => void
  onPageChange: (value: number) => void
  onPageSizeChange: (value: number) => void
  onQueryChange: (value: string) => void
  onRefresh: () => void
  onSortChange: (value: string) => void
  onVectorStatusChange: (value: string) => void
}) {
  const vectorCounts = summary?.vector_counts || {}
  const extensionCounts = summary?.extension_counts || {}
  const extensionOptions = Object.keys(extensionCounts)
    .filter((item) => item && item !== 'unknown')
    .sort()
  const indexedPercent = Math.round((summary?.indexed_ratio || 0) * 100)
  const page = pagination?.page || 1
  const pageCount = pagination?.page_count || 1
  const total = summary?.total || 0
  const filtered = summary?.filtered ?? total
  const vectorStatusOptions = [
    ['all', '全部向量状态'],
    ['indexed', `已向量化 ${vectorCounts.indexed || 0}`],
    ['skipped', `仅原文 ${vectorCounts.skipped || 0}`],
    ['failed', `失败 ${vectorCounts.failed || 0}`],
    ['pending', `待索引 ${vectorCounts.pending || 0}`],
    ['unknown', `未知 ${vectorCounts.unknown || 0}`],
  ]
  const vectorTone = vectorStore?.status === 'ready'
    ? 'border-ops-success/35 text-ops-success'
    : vectorStore?.status === 'missing_embedding_model'
      ? 'border-amber-300/35 text-amber-200'
      : vectorStore?.status === 'needs_attention'
        ? 'border-ops-alert/35 text-ops-alert'
      : 'border-ops-surface1 text-ops-overlay'
  const vectorHealthText = vectorStore?.status_label || (
    vectorStore?.status === 'ready'
      ? 'RAG 可用'
      : vectorStore?.status === 'missing_embedding_model'
        ? '缺少向量模型'
        : vectorStore?.status === 'needs_attention'
          ? '需要处理'
          : '状态待确认'
  )
  const vectorDiagnostics = vectorStore?.diagnostics || []
  const vectorTimeout = vectorStore?.reindex_timeout_seconds || 10

  return (
    <section className="rounded-xl border border-ops-surface0 bg-ops-panel/65 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">资料管理台</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            面向大量资料：搜索、筛选、分页、看向量库状态；召回率不伪造百分比，先看检索命中和证据覆盖。
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="rounded-md border border-ops-surface1 px-3 py-1.5 text-xs text-ops-subtext hover:border-ops-accent hover:text-ops-text"
        >
          刷新状态
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
          <div className="text-[11px] text-ops-overlay">资料总数</div>
          <div className="mt-1 text-2xl font-black text-ops-text">{total}</div>
          <div className="mt-1 text-[11px] text-ops-subtext">当前筛选 {filtered} 份</div>
        </div>
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
          <div className="text-[11px] text-ops-overlay">已向量化</div>
          <div className="mt-1 text-2xl font-black text-ops-success">{vectorCounts.indexed || 0}</div>
          <div className="mt-1 text-[11px] text-ops-subtext">覆盖率 {indexedPercent}%</div>
        </div>
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
          <div className="text-[11px] text-ops-overlay">仅原文/失败</div>
          <div className="mt-1 text-2xl font-black text-amber-200">{(vectorCounts.skipped || 0) + (vectorCounts.failed || 0)}</div>
          <div className="mt-1 text-[11px] text-ops-subtext">仍可查看原文和关键词检索</div>
        </div>
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
          <div className="text-[11px] text-ops-overlay">资料容量</div>
          <div className="mt-1 text-2xl font-black text-ops-text">{formatMemorySize(summary?.total_size || 0)}</div>
          <div className="mt-1 text-[11px] text-ops-subtext">原文留存大小</div>
        </div>
      </div>

      <div className="mt-4 grid gap-2 lg:grid-cols-[minmax(240px,1fr)_170px_150px_150px_120px]">
        <input
          value={query}
          onChange={(event) => {
            onQueryChange(event.target.value)
            onPageChange(1)
          }}
          placeholder="搜索文件名、来源、标签、状态..."
          className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none placeholder:text-ops-overlay focus:border-ops-accent"
        />
        <select
          value={vectorStatus}
          onChange={(event) => {
            onVectorStatusChange(event.target.value)
            onPageChange(1)
          }}
          className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        >
          {vectorStatusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select
          value={extension}
          onChange={(event) => {
            onExtensionChange(event.target.value)
            onPageChange(1)
          }}
          className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        >
          <option value="all">全部类型</option>
          {extensionOptions.map((item) => <option key={item} value={item}>{item} ({extensionCounts[item]})</option>)}
        </select>
        <select
          value={sort}
          onChange={(event) => {
            onSortChange(event.target.value)
            onPageChange(1)
          }}
          className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        >
          <option value="updated_desc">最近更新</option>
          <option value="created_desc">最近上传</option>
          <option value="name_asc">名称 A-Z</option>
          <option value="name_desc">名称 Z-A</option>
          <option value="size_desc">大文件优先</option>
          <option value="size_asc">小文件优先</option>
        </select>
        <select
          value={pageSize}
          onChange={(event) => {
            onPageSizeChange(Number(event.target.value))
            onPageChange(1)
          }}
          className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
        >
          <option value={20}>20/页</option>
          <option value={50}>50/页</option>
          <option value={100}>100/页</option>
          <option value={200}>200/页</option>
        </select>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-[1fr_1fr]">
        <div className={`rounded-lg border bg-ops-dark/35 p-3 ${vectorTone}`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold">向量化模型</span>
            <span className="rounded-full border border-current/35 px-2 py-0.5 text-[10px]">{vectorStore?.status || 'unknown'}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-current/30 px-2 py-0.5 text-[11px] font-semibold">{vectorHealthText}</span>
            <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[11px] text-ops-subtext">
              重建超时 {vectorTimeout} 秒
            </span>
          </div>
          <div className="mt-2 text-xs leading-5 text-ops-subtext">
            模型：{vectorStore?.embedding_model || '未配置'} · 维度：{vectorStore?.embedding_dim || '-'}
          </div>
          <div className="mt-1 text-[11px] leading-5 text-ops-overlay">{vectorStore?.message || '暂无向量化状态。'}</div>
          {vectorStore?.recommended_action && (
            <div className="mt-2 rounded-md border border-current/20 bg-ops-panel/35 px-3 py-2 text-[11px] leading-5">
              下一步：{vectorStore.recommended_action}
            </div>
          )}
        </div>
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold text-ops-text">向量数据库</span>
            <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-subtext">
              {vectorStore?.database || 'LanceDB'}
            </span>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
            <span className="rounded border border-ops-surface1/70 px-2 py-1 text-ops-subtext">表：{vectorStore?.table || '-'}</span>
            <span className="rounded border border-ops-surface1/70 px-2 py-1 text-ops-subtext">目录：{vectorStore?.db_path_exists ? '存在' : '未创建'}</span>
            <span className="rounded border border-ops-surface1/70 px-2 py-1 text-ops-subtext">表状态：{vectorStore?.table_exists ? '可见' : '未确认'}</span>
          </div>
          <div className="mt-2 grid grid-cols-4 gap-2 text-[11px]">
            <span className="rounded border border-ops-success/25 px-2 py-1 text-ops-success">就绪 {vectorStore?.indexed_count ?? vectorCounts.indexed ?? 0}</span>
            <span className="rounded border border-amber-300/25 px-2 py-1 text-amber-200">原文 {vectorStore?.skipped_count ?? vectorCounts.skipped ?? 0}</span>
            <span className="rounded border border-ops-alert/25 px-2 py-1 text-ops-alert">失败 {vectorStore?.failed_count ?? vectorCounts.failed ?? 0}</span>
            <span className="rounded border border-ops-surface1 px-2 py-1 text-ops-subtext">待处理 {vectorStore?.pending_count ?? vectorCounts.pending ?? 0}</span>
          </div>
          <div className="mt-2 truncate text-[11px] text-ops-overlay" title={vectorStore?.db_path || ''}>
            路径：{vectorStore?.db_path || '-'}
          </div>
          {vectorDiagnostics.length > 0 && (
            <div className="mt-2 space-y-1 text-[11px] leading-5 text-ops-overlay">
              {vectorDiagnostics.map((item) => <div key={item}>说明：{item}</div>)}
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-ops-surface0 bg-ops-dark/30 px-3 py-2 text-xs text-ops-subtext">
        <div>第 {page} / {pageCount} 页 · 当前 {pagination?.total || 0} 条筛选结果</div>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={!pagination?.has_prev}
            onClick={() => onPageChange(Math.max(1, page - 1))}
            className="rounded border border-ops-surface1 px-3 py-1 hover:border-ops-accent hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-40"
          >
            上一页
          </button>
          <button
            type="button"
            disabled={!pagination?.has_next}
            onClick={() => onPageChange(page + 1)}
            className="rounded border border-ops-surface1 px-3 py-1 hover:border-ops-accent hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-40"
          >
            下一页
          </button>
        </div>
      </div>
    </section>
  )
}

export function KnowledgeFileCard({
  file,
  onOpen,
  onReindex,
  onDelete,
  reindexing,
}: {
  file: KnowledgeFile
  onOpen: (file: KnowledgeFile) => void
  onReindex: (file: KnowledgeFile) => void
  onDelete: (file: KnowledgeFile) => void
  reindexing: boolean
}) {
  const kind = knowledgeFileKind(file.filename)
  const title = file.original_filename || file.filename
  const canReindex = file.vector_status !== 'indexed'
  return (
    <div className="bg-ops-panel border border-ops-surface0 rounded-lg px-4 py-3 flex items-start gap-3 hover:border-ops-accent/40 transition-colors">
      <span className={`grid h-9 w-12 shrink-0 place-items-center rounded border bg-ops-dark text-[11px] font-semibold ${kind.className}`}>{kind.label}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-ops-text truncate" title={title}>{title}</div>
        <div className="mt-1 flex flex-wrap gap-2 text-[11px]">
          <span className="rounded-full border border-ops-accent/30 px-2 py-0.5 text-ops-accent">资料状态：{knowledgeStatusLabel(file)}</span>
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-overlay">向量状态：{vectorStatusLabel(file)}</span>
          {file.obsidian_compatible && (
            <span className="rounded-full border border-ops-success/30 px-2 py-0.5 text-ops-success">可导出</span>
          )}
          {file.size !== undefined && (
            <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-overlay">{(file.size / 1024).toFixed(1)} KB</span>
          )}
        </div>
        <div className="mt-2 space-y-1 text-[11px] leading-5 text-ops-overlay">
          {file.source_path && <div className="truncate" title={file.source_path}>原文：{file.source_path}</div>}
          {file.note_path && <div className="truncate" title={file.note_path}>来源记录：{ragDisplayPath(file.note_path)}</div>}
          {file.vector_error && <div className="line-clamp-2 text-ops-muted">RAG 提示：{ragErrorHint(file.vector_error)}</div>}
        </div>
      </div>
      <div className="flex shrink-0 flex-col gap-2">
        <button
          onClick={() => onOpen(file)}
          className="rounded-lg border border-ops-accent/35 px-2 py-1 text-xs font-semibold text-ops-accent transition-colors hover:bg-ops-accent/10"
          title="查看上传资料内容"
        >
          查看内容
        </button>
        <button
          onClick={() => onReindex(file)}
          disabled={reindexing || !canReindex}
          className="rounded-lg border border-ops-success/35 px-2 py-1 text-xs font-semibold text-ops-success transition-colors hover:bg-ops-success/10 disabled:cursor-not-allowed disabled:opacity-45"
          title={canReindex ? '使用当前向量化模型重建索引' : '该资料已完成向量化'}
        >
          {reindexing ? '重建中...' : '重建向量'}
        </button>
        <button
          onClick={() => onDelete(file)}
          className="rounded-lg px-2 py-1 text-xs text-ops-overlay transition-colors hover:bg-ops-alert/10 hover:text-ops-alert"
          title="删除"
        >
          删除
        </button>
      </div>
    </div>
  )
}

export function KnowledgeCompileQueuePanel({
  compilingSourceSession,
  items,
  onCompile,
}: {
  compilingSourceSession: string | null
  items: KnowledgeCompileQueueItem[]
  onCompile: (item: KnowledgeCompileQueueItem) => void
}) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">AI 摘要队列</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            RAG 主线已经保存原文和检索索引；这里把重要内容生成摘要，作为全局共享知识供后续会话检索和图谱追溯。
          </p>
        </div>
        <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-xs text-ops-accent">
          {items.length}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => (
          <article key={item.id || item.filename} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-xs font-semibold text-ops-text" title={item.original_filename || item.filename}>
                  {item.original_filename || item.filename}
                </div>
                <div className="mt-1 font-mono text-[11px] text-ops-overlay">
              {item.source_session_id || item.id}
                </div>
              </div>
              <span className="shrink-0 rounded-full border border-ops-accent/30 px-2 py-0.5 text-[10px] text-ops-accent">
                {item.compile_stage || 'queued'}
              </span>
            </div>
            <p className="mt-2 text-xs leading-5 text-ops-subtext">
              {item.status_label || knowledgeStatusLabel(item)}
            </p>
            {item.source_path && (
              <div className="mt-2 truncate rounded border border-ops-surface1/70 bg-ops-panel/40 px-2 py-1 font-mono text-[11px] text-ops-overlay" title={item.source_path}>
                原文：{item.source_path}
              </div>
            )}
            {item.note_path && (
              <div className="mt-1 truncate rounded border border-ops-surface1/70 bg-ops-panel/40 px-2 py-1 font-mono text-[11px] text-ops-overlay" title={item.note_path}>
                资料：{ragDisplayPath(item.note_path)}
              </div>
            )}
            {item.candidate_path && (
              <div className="mt-1 truncate rounded border border-ops-success/30 bg-ops-success/5 px-2 py-1 font-mono text-[11px] text-ops-success" title={item.candidate_path}>
                摘要：{ragDisplayPath(item.candidate_path)}
              </div>
            )}
            <button
              onClick={() => onCompile(item)}
              disabled={Boolean(compilingSourceSession) || item.compile_stage === 'candidate_generated'}
              className="mt-2 w-full rounded-md border border-ops-accent/40 px-3 py-1.5 text-xs font-semibold text-ops-accent transition-colors hover:bg-ops-accent/10 disabled:cursor-not-allowed disabled:opacity-45"
            >
              {compilingSourceSession === (item.source_session_id || item.id)
                ? '整理中...'
                : item.compile_stage === 'candidate_generated'
                  ? '摘要已生成'
                  : '生成 AI 摘要'}
            </button>
          </article>
        )) : (
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-6 text-center text-xs leading-5 text-ops-overlay">
            暂无需要生成摘要的资料。RAG 检索会直接使用已入库原文。
          </div>
        )}
      </div>
    </section>
  )
}

export function KnowledgeVaultSearchPanel({
  query,
  results,
  scope,
  searching,
  onQueryChange,
  onScopeChange,
  onSearch,
}: {
  query: string
  results: KnowledgeVaultSearchResult[]
  scope: string
  searching: boolean
  onQueryChange: (value: string) => void
  onScopeChange: (value: string) => void
  onSearch: () => void
}) {
  const scopes = [
    ['all', '全部资料'],
    ['articles', 'RAG 资料'],
    ['candidates', 'AI 摘要'],
    ['sources', '来源记录'],
    ['raw', '原始资料'],
  ]
  const sourceCount = new Set(results.map((item) => item.source_session_id || item.id || item.path).filter(Boolean)).size
  const topScore = results.length > 0 ? Math.max(...results.map((item) => Number(item.score) || 0)) : 0

  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">RAG 召回测试</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            输入一个准备问 AI 的问题，先看知识库能不能找到可追溯证据；这里只做召回验证，不做复杂评测系统。
          </p>
        </div>
        <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-xs text-ops-accent">
          {results.length}
        </span>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
          <div className="text-[11px] text-ops-overlay">命中证据</div>
          <div className="mt-1 text-lg font-black text-ops-text">{results.length}</div>
        </div>
        <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
          <div className="text-[11px] text-ops-overlay">来源数量</div>
          <div className="mt-1 text-lg font-black text-ops-text">{sourceCount}</div>
        </div>
        <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
          <div className="text-[11px] text-ops-overlay">最高相关度</div>
          <div className="mt-1 text-lg font-black text-ops-text">{topScore}</div>
        </div>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_130px]">
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') onSearch()
          }}
          placeholder="例如：172.17.8.131 的 SSH 风险是什么？"
          className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent"
        />
        <select
          value={scope}
          onChange={(event) => onScopeChange(event.target.value)}
          className="rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none transition-colors focus:border-ops-accent"
        >
          {scopes.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>
      <button
        onClick={onSearch}
        disabled={searching}
        className="mt-2 w-full rounded-md border border-ops-accent/40 px-3 py-1.5 text-xs font-semibold text-ops-accent transition-colors hover:bg-ops-accent/10 disabled:cursor-not-allowed disabled:opacity-45"
      >
        {searching ? '召回中...' : '执行召回测试'}
      </button>
      <div className="mt-3 space-y-2">
        {results.length > 0 ? results.map((item, index) => (
          <article key={`${item.path}-${index}`} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-xs font-semibold text-ops-text" title={item.title}>#{index + 1} {item.title}</div>
                <div className="mt-1 truncate font-mono text-[11px] text-ops-overlay" title={item.path}>{ragDisplayPath(item.path)}</div>
              </div>
              <span className="shrink-0 rounded-full border border-ops-accent/30 px-2 py-0.5 text-[10px] text-ops-accent">
                {ragKindLabel(item.kind_label)}
              </span>
            </div>
            <p className="mt-2 line-clamp-3 text-xs leading-5 text-ops-subtext">{item.snippet}</p>
            <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-ops-overlay">
              {(item.source_session_id || item.id) && <span>来源：{item.source_session_id || item.id}</span>}
              {item.compile_stage && <span>状态：{item.compile_stage}</span>}
              <span>相关度：{item.score}</span>
            </div>
          </article>
        )) : (
          <div className="rounded-md border border-dashed border-ops-surface1 p-3 text-xs leading-5 text-ops-subtext">
            输入问题后会展示命中的资料、证据片段、来源和相关度。即使 Embedding 暂不可用，原文仍可作为可追溯证据。
          </div>
        )}
      </div>
    </section>
  )
}

export function KnowledgeVaultGraphPanel({
  graph,
  includeCandidates,
  loading,
  onIncludeCandidatesChange,
  onLoad,
}: {
  graph: KnowledgeVaultGraph | null
  includeCandidates: boolean
  loading: boolean
  onIncludeCandidatesChange: (value: boolean) => void
  onLoad: () => void
}) {
  const topNodes = graph?.nodes
    .slice()
    .sort((a, b) => (b.degree || 0) - (a.degree || 0))
    .slice(0, 8) || []
  const topEdges = graph?.edges.slice(0, 10) || []
  const nodeById = new Map((graph?.nodes || []).map((node) => [node.id, node]))
  const relationCounts = graph?.summary.relation_counts || {}
  const hasGraphLinks = Boolean(graph && graph.nodes.length > 0)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [graphZoom, setGraphZoom] = useState(1)
  const [graphPan, setGraphPan] = useState({ x: 0, y: 0 })
  const [dragStart, setDragStart] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null)
  const selectedNode = selectedNodeId ? nodeById.get(selectedNodeId) : topNodes[0]
  const selectedNodeEdges = selectedNode && graph
    ? graph.edges.filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id).slice(0, 8)
    : []
  const viewWidth = 100 / graphZoom
  const viewHeight = 64 / graphZoom
  const viewBox = `${(100 - viewWidth) / 2 + graphPan.x} ${(64 - viewHeight) / 2 + graphPan.y} ${viewWidth} ${viewHeight}`
  const resetGraphView = () => {
    setGraphZoom(1)
    setGraphPan({ x: 0, y: 0 })
    setDragStart(null)
  }

  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">知识图谱</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            RAG 负责检索证据，图谱负责看资料之间是否有关联。
          </p>
        </div>
        <span className="rounded-full border border-ops-success/35 px-2 py-0.5 text-xs text-ops-success">
          {graph?.summary.node_count || 0} 节点 / {graph?.summary.edge_count || 0} 关系
        </span>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto]">
        <label className="flex items-center gap-2 rounded-md border border-ops-surface0 bg-ops-dark/30 px-3 py-2 text-xs text-ops-subtext">
          <input
            type="checkbox"
            checked={includeCandidates}
            onChange={(event) => onIncludeCandidatesChange(event.target.checked)}
            className="accent-ops-accent"
          />
          包含 AI 摘要
        </label>
        <button
          onClick={onLoad}
          disabled={loading}
          className="rounded-md border border-ops-success/40 px-4 py-2 text-xs font-semibold text-ops-success transition-colors hover:bg-ops-success/10 disabled:cursor-not-allowed disabled:opacity-45"
        >
          {loading ? '生成中...' : '生成图谱'}
        </button>
      </div>
      {graph ? (
        <div className="mt-3 space-y-3">
          <div className="grid grid-cols-2 gap-2 text-xs lg:grid-cols-4">
            <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-2">
              <div className="text-ops-overlay">正式资料</div>
              <div className="mt-1 text-lg font-semibold text-ops-text">{graph.summary.article_count}</div>
            </div>
            <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-2">
              <div className="text-ops-overlay">AI 摘要</div>
              <div className="mt-1 text-lg font-semibold text-ops-text">{graph.summary.candidate_count}</div>
            </div>
            <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-2">
              <div className="text-ops-overlay">已连接</div>
              <div className="mt-1 text-lg font-semibold text-ops-text">{graph.summary.linked_node_count || 0}</div>
            </div>
            <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-2">
              <div className="text-ops-overlay">孤立知识</div>
              <div className="mt-1 text-lg font-semibold text-ops-text">{graph.summary.isolated_node_count || 0}</div>
            </div>
          </div>

          <div className="rounded-xl border border-ops-accent/25 bg-[radial-gradient(circle_at_18%_18%,rgba(45,212,191,0.2),transparent_30%),radial-gradient(circle_at_82%_20%,rgba(96,165,250,0.16),transparent_28%),linear-gradient(135deg,rgba(8,13,28,0.98),rgba(8,30,48,0.78))] p-3 shadow-[0_24px_90px_rgba(0,0,0,0.28)]">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div>
                <span className="font-semibold text-ops-text">可视化知识图谱</span>
                <span className="ml-2 rounded-full border border-ops-accent/35 px-2 py-0.5 text-[10px] text-ops-accent">
                  可缩放 · 可拖动 · 可点选
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-ops-subtext">
                  关联关系 {relationCounts.wikilink || 0} / 内容提及 {relationCounts.mention || 0}
                </span>
                <button
                  type="button"
                  onClick={() => setGraphZoom((value) => Math.max(0.75, Number((value - 0.25).toFixed(2))))}
                  className="rounded border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext hover:border-ops-accent hover:text-ops-accent"
                >
                  缩小
                </button>
                <button
                  type="button"
                  onClick={() => setGraphZoom((value) => Math.min(2.5, Number((value + 0.25).toFixed(2))))}
                  className="rounded border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext hover:border-ops-accent hover:text-ops-accent"
                >
                  放大
                </button>
                <button
                  type="button"
                  onClick={resetGraphView}
                  className="rounded border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext hover:border-ops-accent hover:text-ops-accent"
                >
                  居中
                </button>
              </div>
            </div>
            {hasGraphLinks ? (
              <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_300px]">
                <div className="relative overflow-hidden rounded-lg border border-ops-surface0 bg-[linear-gradient(rgba(45,212,191,0.07)_1px,transparent_1px),linear-gradient(90deg,rgba(45,212,191,0.07)_1px,transparent_1px),rgba(2,6,23,0.72)] bg-[size:24px_24px]">
                  <svg
                    viewBox={viewBox}
                    role="img"
                    aria-label="知识图谱"
                    className="h-[410px] w-full cursor-grab select-none overflow-visible active:cursor-grabbing"
                    onWheel={(event) => {
                      event.preventDefault()
                      setGraphZoom((value) => Math.min(2.5, Math.max(0.75, Number((value + (event.deltaY > 0 ? -0.12 : 0.12)).toFixed(2)))))
                    }}
                    onPointerDown={(event) => {
                      setDragStart({ x: event.clientX, y: event.clientY, panX: graphPan.x, panY: graphPan.y })
                    }}
                    onPointerMove={(event) => {
                      if (!dragStart) return
                      const scale = 0.18 / graphZoom
                      setGraphPan({
                        x: dragStart.panX - (event.clientX - dragStart.x) * scale,
                        y: dragStart.panY - (event.clientY - dragStart.y) * scale,
                      })
                    }}
                    onPointerUp={() => setDragStart(null)}
                    onPointerLeave={() => setDragStart(null)}
                  >
                    <defs>
                      <filter id="knowledgeGraphGlow" x="-40%" y="-40%" width="180%" height="180%">
                        <feGaussianBlur stdDeviation="1.8" result="coloredBlur" />
                        <feMerge>
                          <feMergeNode in="coloredBlur" />
                          <feMergeNode in="SourceGraphic" />
                        </feMerge>
                      </filter>
                      <linearGradient id="knowledgeGraphEdge" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="rgba(45,212,191,0.9)" />
                        <stop offset="100%" stopColor="rgba(96,165,250,0.52)" />
                      </linearGradient>
                    </defs>
                    {graph.edges.map((edge, index) => {
                      const source = nodeById.get(edge.source)
                      const target = nodeById.get(edge.target)
                      if (!source || !target) return null
                      const isSelectedEdge = selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id)
                      return (
                        <line
                          key={`${edge.source}-${edge.target}-${edge.kind}-${index}`}
                          x1={source.x || 50}
                          y1={source.y || 32}
                          x2={target.x || 50}
                          y2={target.y || 32}
                          stroke={isSelectedEdge ? 'url(#knowledgeGraphEdge)' : edge.kind === 'wikilink' ? 'rgba(45,212,191,0.6)' : 'rgba(148,163,184,0.28)'}
                          strokeWidth={isSelectedEdge ? 0.92 : edge.kind === 'wikilink' ? 0.52 : 0.32}
                          strokeLinecap="round"
                          opacity={selectedNode ? (isSelectedEdge ? 1 : 0.24) : 1}
                        />
                      )
                    })}
                    {graph.nodes.map((node) => {
                      const isSelected = selectedNode?.id === node.id
                      const isNeighbor = selectedNodeEdges.some((edge) => edge.source === node.id || edge.target === node.id)
                      const muted = selectedNode && !isSelected && !isNeighbor
                      const radius = Math.max(2.4, (node.size || 8) / 2.65) + (isSelected ? 1.35 : 0)
                      return (
                        <g
                          key={node.id}
                          role="button"
                          tabIndex={0}
                          filter={(node.degree || 0) > 0 ? 'url(#knowledgeGraphGlow)' : undefined}
                          onClick={(event) => {
                            event.stopPropagation()
                            setSelectedNodeId(node.id)
                          }}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') setSelectedNodeId(node.id)
                          }}
                          className="cursor-pointer outline-none transition-opacity"
                          opacity={muted ? 0.28 : 1}
                        >
                          <circle
                            cx={node.x || 50}
                            cy={node.y || 32}
                            r={radius + 1.1}
                            fill={isSelected ? 'rgba(45,212,191,0.18)' : 'rgba(15,23,42,0.18)'}
                            stroke={isSelected ? 'rgba(45,212,191,0.96)' : 'rgba(148,163,184,0.26)'}
                            strokeWidth={isSelected ? 0.5 : 0.2}
                          />
                          <circle
                            cx={node.x || 50}
                            cy={node.y || 32}
                            r={radius}
                            fill={node.kind === 'article' ? 'rgba(45,212,191,0.9)' : 'rgba(251,191,36,0.82)'}
                            stroke="rgba(226,232,240,0.78)"
                            strokeWidth="0.28"
                          />
                          <text
                            x={(node.x || 50) + radius + 1.4}
                            y={(node.y || 32) + 1}
                            fill={isSelected ? 'rgba(255,255,255,0.98)' : 'rgba(226,232,240,0.84)'}
                            fontSize={isSelected ? '3.1' : '2.55'}
                            fontWeight={isSelected ? 700 : 500}
                            paintOrder="stroke"
                            stroke="rgba(2,6,23,0.88)"
                            strokeWidth="0.7"
                          >
                            {node.title.slice(0, 20)}
                          </text>
                        </g>
                      )
                    })}
                  </svg>
                  <div className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap gap-2 text-[10px] text-ops-subtext">
                    <span className="rounded-full border border-ops-accent/30 bg-ops-dark/70 px-2 py-1">青色：RAG 资料</span>
                    <span className="rounded-full border border-amber-300/30 bg-ops-dark/70 px-2 py-1">黄色：AI 摘要</span>
                    <span className="rounded-full border border-ops-surface1 bg-ops-dark/70 px-2 py-1">滚轮缩放，拖动移动</span>
                  </div>
                </div>
                <aside className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-xs font-semibold text-ops-text">节点详情</div>
                      <p className="mt-1 text-[11px] leading-5 text-ops-overlay">点击图谱节点查看它连接了哪些知识。</p>
                    </div>
                    <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-[10px] text-ops-accent">
                      {graphZoom.toFixed(2)}x
                    </span>
                  </div>
                  {selectedNode ? (
                    <div className="mt-3 space-y-3">
                      <div className="rounded-md border border-ops-accent/25 bg-ops-accent/10 px-3 py-2">
                        <div className="text-sm font-semibold text-ops-text">{selectedNode.title}</div>
                        <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-ops-subtext">
                          <span>{selectedNode.kind === 'article' ? 'RAG 资料' : 'AI 摘要'}</span>
                          <span>{selectedNode.degree || 0} 个关系</span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        {selectedNodeEdges.length > 0 ? selectedNodeEdges.map((edge, index) => {
                          const peerId = edge.source === selectedNode.id ? edge.target : edge.source
                          const peer = nodeById.get(peerId)
                          return (
                            <button
                              type="button"
                              key={`${edge.source}-${edge.target}-${index}`}
                              onClick={() => peer && setSelectedNodeId(peer.id)}
                              className="w-full rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2 text-left transition-colors hover:border-ops-accent/45 hover:bg-ops-accent/10"
                            >
                              <div className="truncate text-xs font-semibold text-ops-text">{peer?.title || peerId}</div>
                              <div className="mt-1 text-[11px] text-ops-overlay">
                                {edge.kind === 'wikilink' ? '显式关联' : '内容提及'} · 点击跳转
                              </div>
                            </button>
                          )
                        }) : (
                          <div className="rounded-md border border-dashed border-ops-surface1 p-3 text-xs leading-5 text-ops-subtext">
                            这个节点暂时没有关系，可以在资料内容里补充关联。
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="mt-3 rounded-md border border-dashed border-ops-surface1 p-4 text-xs leading-5 text-ops-subtext">
                      先点击左侧任意节点。
                    </div>
                  )}
                </aside>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-ops-surface1 p-6 text-center text-xs leading-6 text-ops-subtext">
                暂无可绘制节点。资料之间出现相同主题、资产、命令或显式关联后，这里会形成关系图。
              </div>
            )}
          </div>

          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-3">
            <div className="text-xs font-semibold text-ops-text">核心节点</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {topNodes.length > 0 ? topNodes.map((node) => (
                <span key={node.id} className="max-w-full truncate rounded-full border border-ops-accent/25 px-2 py-1 text-[11px] text-ops-accent" title={node.path}>
                  {node.kind === 'article' ? 'RAG 资料' : 'AI 摘要'} · {node.title} · {node.degree || 0} 连接
                </span>
              )) : <span className="text-xs text-ops-subtext">暂无节点</span>}
            </div>
          </div>
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-3">
            <div className="text-xs font-semibold text-ops-text">关系明细</div>
            <div className="mt-2 space-y-1">
              {topEdges.length > 0 ? topEdges.map((edge, index) => {
                const source = nodeById.get(edge.source)
                const target = nodeById.get(edge.target)
                return (
                  <div key={`${edge.source}-${edge.target}-${index}`} className="truncate font-mono text-[11px] text-ops-subtext" title={`${edge.source} -> ${edge.target}`}>
                    {edge.label}: {source?.title || edge.source} {'->'} {target?.title || edge.target}
                  </div>
                )
              }) : <div className="text-xs text-ops-subtext">暂无关系，后续可在资料中补充关联。</div>}
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-3 rounded-md border border-dashed border-ops-surface1 p-3 text-xs leading-5 text-ops-subtext">
          点击生成后会扫描资料库，不依赖外部数据库，适合离线部署和来源追溯。
        </div>
      )}
    </section>
  )
}

export function KnowledgeCandidatePanel({
  approvingSourceSession,
  items,
  openingCandidate,
  onApprove,
  onOpen,
}: {
  approvingSourceSession: string | null
  items: KnowledgeCompileQueueItem[]
  openingCandidate: string | null
  onApprove: (item: KnowledgeCompileQueueItem) => void
  onOpen: (item: KnowledgeCompileQueueItem) => void
}) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">AI 摘要</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            AI 摘要用于把重点内容变成更容易引用的 Markdown，不影响原文检索。
          </p>
        </div>
        <span className="rounded-full border border-ops-success/35 px-2 py-0.5 text-xs text-ops-success">
          {items.length}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => {
          const sourceSession = item.source_session_id || item.id
          const approved = item.compile_stage === 'wiki_approved' || item.review_status === 'approved'
          return (
            <article key={`${item.id || item.filename}-candidate`} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-xs font-semibold text-ops-text" title={item.original_filename || item.filename}>
                    {item.original_filename || item.filename}
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-ops-overlay">{sourceSession}</div>
                </div>
                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] ${approved ? 'border-ops-success/30 text-ops-success' : 'border-amber-300/35 text-amber-200'}`}>
                  {approved ? '已入库' : '待确认'}
                </span>
              </div>
              {item.candidate_path && (
                <div className="mt-2 truncate rounded border border-ops-surface1/70 bg-ops-panel/40 px-2 py-1 font-mono text-[11px] text-ops-overlay" title={item.candidate_path}>
                  candidate: {item.candidate_path}
                </div>
              )}
              {item.wiki_path && (
                <div className="mt-1 truncate rounded border border-ops-success/30 bg-ops-success/5 px-2 py-1 font-mono text-[11px] text-ops-success" title={item.wiki_path}>
                  资料：{ragDisplayPath(item.wiki_path)}
                </div>
              )}
              <div className="mt-2 grid grid-cols-2 gap-2">
                <button
                  onClick={() => onOpen(item)}
                  disabled={Boolean(openingCandidate) || item.candidate_exists === false}
                  className="rounded-md border border-ops-accent/40 px-3 py-1.5 text-xs font-semibold text-ops-accent transition-colors hover:bg-ops-accent/10 disabled:cursor-not-allowed disabled:opacity-45"
                >
                  {openingCandidate === sourceSession ? '打开中...' : '预览/编辑'}
                </button>
                <button
                  onClick={() => onApprove(item)}
                  disabled={Boolean(approvingSourceSession) || approved || !item.candidate_exists}
                  className="rounded-md border border-ops-success/40 px-3 py-1.5 text-xs font-semibold text-ops-success transition-colors hover:bg-ops-success/10 disabled:cursor-not-allowed disabled:opacity-45"
                >
                  {approvingSourceSession === sourceSession
                    ? '批准中...'
                    : approved
                      ? '已入库'
                      : item.candidate_exists === false
                        ? '缺失'
                        : '批准入库'}
                </button>
              </div>
            </article>
          )
        }) : (
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-6 text-center text-xs leading-5 text-ops-overlay">
            暂无 AI 摘要。需要长期引用的内容可以先生成摘要。
          </div>
        )}
      </div>
    </section>
  )
}

export function KnowledgeCandidateEditor({
  candidate,
  draft,
  saving,
  onDraftChange,
  onSave,
}: {
  candidate: KnowledgeCompileQueueItem | null
  draft: string
  saving: boolean
  onDraftChange: (value: string) => void
  onSave: () => void
}) {
  if (!candidate) {
    return (
      <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
        <div className="text-sm font-semibold text-ops-text">摘要正文</div>
        <p className="mt-1 text-xs leading-5 text-ops-subtext">
          点击 AI 摘要的“预览/编辑”，这里会显示 Markdown 正文，可直接修改后保存。
        </p>
      </section>
    )
  }
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60">
      <div className="border-b border-ops-surface0 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs font-semibold text-ops-accent">摘要正文</div>
            <h2 className="mt-1 truncate text-sm font-bold text-ops-text" title={candidate.candidate_path || candidate.original_filename || candidate.filename}>
              {candidate.candidate_path || candidate.original_filename || candidate.filename}
            </h2>
          </div>
          <button
            onClick={onSave}
            disabled={saving || !draft.trim()}
            className="shrink-0 rounded-lg bg-ops-accent px-3 py-1.5 text-xs font-semibold text-ops-dark disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存摘要'}
          </button>
        </div>
        <div className="mt-1 text-xs text-ops-overlay">
          {candidate.source_session_id || candidate.id} · {candidate.content_sha256 ? `sha256 ${candidate.content_sha256.slice(0, 10)}` : '未计算哈希'}
        </div>
      </div>
      <textarea
        value={draft}
        onChange={(event) => onDraftChange(event.target.value)}
        className="min-h-[420px] w-full resize-y bg-transparent p-4 font-mono text-xs leading-5 text-ops-subtext outline-none"
      />
    </section>
  )
}

export function KnowledgeArticlePanel({
  items,
  openingArticle,
  onOpen,
}: {
  items: KnowledgeCompileQueueItem[]
  openingArticle: string | null
  onOpen: (item: KnowledgeCompileQueueItem) => void
}) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">RAG 资料</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            这里展示可长期引用的 RAG 资料；它属于全局共享知识，后续会话、画像和检索都可以使用。
          </p>
        </div>
        <span className="rounded-full border border-ops-success/35 px-2 py-0.5 text-xs text-ops-success">
          {items.length}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => {
          const sourceSession = item.source_session_id || item.id
          return (
            <article key={`${item.id || item.filename}-article`} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-xs font-semibold text-ops-text" title={item.original_filename || item.filename}>
                    {item.original_filename || item.filename}
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-ops-overlay">{sourceSession}</div>
                </div>
                <span className="shrink-0 rounded-full border border-ops-success/30 px-2 py-0.5 text-[10px] text-ops-success">
                  正式
                </span>
              </div>
              {item.wiki_path && (
                <div className="mt-2 truncate rounded border border-ops-success/30 bg-ops-success/5 px-2 py-1 font-mono text-[11px] text-ops-success" title={item.wiki_path}>
                  资料：{ragDisplayPath(item.wiki_path)}
                </div>
              )}
              <button
                onClick={() => onOpen(item)}
                disabled={Boolean(openingArticle) || item.article_exists === false}
                className="mt-2 w-full rounded-md border border-ops-accent/40 px-3 py-1.5 text-xs font-semibold text-ops-accent transition-colors hover:bg-ops-accent/10 disabled:cursor-not-allowed disabled:opacity-45"
              >
                {openingArticle === sourceSession ? '打开中...' : item.article_exists === false ? '资料缺失' : '打开 RAG 资料'}
              </button>
            </article>
          )
        }) : (
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-6 text-center text-xs leading-5 text-ops-overlay">
            暂无 RAG 资料。资料入库后，这里会出现可引用的长期知识。
          </div>
        )}
      </div>
    </section>
  )
}

export function KnowledgeArticleViewer({ article }: { article: KnowledgeCompileQueueItem | null }) {
  if (!article) {
    return (
      <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
        <div className="text-sm font-semibold text-ops-text">RAG 正文</div>
        <p className="mt-1 text-xs leading-5 text-ops-subtext">
          点击 RAG 资料的“打开 RAG 资料”，这里会以只读方式展示 Markdown 正文。
        </p>
      </section>
    )
  }
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60">
      <div className="border-b border-ops-surface0 px-4 py-3">
        <div className="text-xs font-semibold text-ops-success">RAG 正文</div>
        <h2 className="mt-1 truncate text-sm font-bold text-ops-text" title={article.wiki_path || article.original_filename || article.filename}>
          {ragDisplayPath(article.wiki_path) || article.original_filename || article.filename}
        </h2>
        <div className="mt-1 text-xs text-ops-overlay">
          {article.source_session_id || article.id} · {article.content_sha256 ? `sha256 ${article.content_sha256.slice(0, 10)}` : '未计算哈希'}
        </div>
      </div>
      <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap p-4 font-mono text-xs leading-5 text-ops-subtext">
        {article.content || '该 RAG 资料暂无正文'}
      </pre>
    </section>
  )
}

export function KnowledgeEmptyState({
  uploading,
  onUpload,
}: {
  uploading: boolean
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-6">
        <div className="text-sm font-semibold text-ops-text">知识库为空</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ops-subtext">
          上传巡检 SOP、故障处理记录、系统架构说明、日志样例、表格、图片或 HTML 后，OpsCore 会先保存原始资料并进入 RAG 检索。
        </p>
        <label className="mt-5 inline-flex cursor-pointer rounded-lg bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark transition-colors hover:bg-ops-accent/85">
          上传第一份文档
          <UploadInput disabled={uploading} onUpload={onUpload} />
        </label>
      </section>
      <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
        {[
          ['支持格式', 'PDF、Markdown、TXT、Word、Excel、CSV、HTML、日志、图片'],
          ['资料留底', '原始文件不被 AI 修改，来源记录保留路径和状态'],
          ['RAG 检索', 'AI 后续可引用命中证据、资产画像、故障案例和关联索引'],
        ].map(([title, desc]) => (
          <div key={title} className="rounded-lg border border-ops-surface0 bg-ops-dark/35 p-4">
            <div className="text-sm font-semibold text-ops-text">{title}</div>
            <p className="mt-2 text-xs leading-5 text-ops-subtext">{desc}</p>
          </div>
        ))}
      </section>
    </div>
  )
}

export function KnowledgeDeleteDialog({
  deleting,
  target,
  onCancel,
  onConfirm,
}: {
  deleting: boolean
  target: KnowledgeFile
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={() => !deleting && onCancel()}>
      <section className="w-full max-w-md rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="border-b border-ops-surface0 px-5 py-4">
          <div className="text-xs font-semibold text-ops-alert">删除知识库文档</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">确认删除</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">
            删除后该文档不会再参与知识检索，已生成的历史会话内容不会被自动修改。
          </p>
        </div>
        <div className="p-5">
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 px-3 py-2">
            <div className="break-all text-sm font-semibold text-ops-text">{target.filename}</div>
            <div className="mt-1 text-xs text-ops-overlay">
              {target.chunks !== undefined && `${target.chunks} 个向量块`}
              {target.size !== undefined && ` · ${(target.size / 1024).toFixed(1)} KB`}
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-4">
          <button
            onClick={onCancel}
            disabled={deleting}
            className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="rounded-lg bg-ops-alert px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {deleting ? '删除中...' : '确认删除'}
          </button>
        </div>
      </section>
    </div>
  )
}

export function KnowledgeDocumentPreviewDialog({
  content,
  loading,
  target,
  onClose,
}: {
  content: KnowledgeDocumentContent | null
  loading: boolean
  target: KnowledgeFile
  onClose: () => void
}) {
  const title = content?.original_filename || target.original_filename || target.filename
  const body = content?.content || ''
  const isSourceNote = content?.content_type === 'source_note'
  const isMetadata = content?.content_type === 'metadata'
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={() => !loading && onClose()}>
      <section className="flex max-h-[88vh] w-full max-w-5xl flex-col rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="border-b border-ops-surface0 px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs font-semibold text-ops-accent">资料内容预览</div>
              <h2 className="mt-1 truncate text-lg font-bold text-ops-text" title={title}>{title}</h2>
              <p className="mt-1 text-sm leading-6 text-ops-subtext">
                这里显示你上传到资料库的原文或来源记录；向量状态只说明能否语义检索，不影响原文留存。
              </p>
            </div>
            <button onClick={onClose} disabled={loading} className="rounded-lg border border-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext hover:text-ops-text disabled:opacity-50">
              关闭
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
            <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-overlay">文件：{target.filename}</span>
            {content?.extension && <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-overlay">格式：{content.extension}</span>}
            <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-overlay">向量状态：{vectorStatusLabel(content || target)}</span>
            {content?.truncated && <span className="rounded-full border border-amber-300/35 px-2 py-0.5 text-amber-200">内容较长，已截取前 {content.preview_limit} 字符</span>}
            {isSourceNote && <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-ops-accent">复杂文件，展示来源记录</span>}
            {isMetadata && <span className="rounded-full border border-amber-300/35 px-2 py-0.5 text-amber-200">复杂文件暂不直接预览</span>}
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-5">
          {loading ? (
            <div className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-8 text-center text-sm text-ops-subtext">
              正在读取资料内容...
            </div>
          ) : (
            <pre className="min-h-[320px] whitespace-pre-wrap break-words rounded-lg border border-ops-surface0 bg-ops-dark/65 p-4 font-mono text-xs leading-6 text-ops-subtext">
              {body || '没有可预览的内容。'}
            </pre>
          )}
        </div>
      </section>
    </div>
  )
}

export function MemoryItemCard({
  item,
  selected,
  onOpen,
  onDelete,
}: {
  item: MemoryItem
  selected: boolean
  onOpen: (item: MemoryItem) => void
  onDelete: (item: MemoryItem) => void
}) {
  const scopeLabel = item.scope_id.startsWith('asset:')
    ? '资产'
    : item.scope_id.startsWith('asset-host:')
      ? '主机'
      : item.scope_id.startsWith('asset-kind:')
        ? '类型'
        : '会话'
  const mainKind = dominantMemoryKind(item)
  return (
    <article className={`rounded-lg border bg-ops-panel px-4 py-3 transition-colors ${selected ? 'border-ops-accent/70' : 'border-ops-surface0 hover:border-ops-accent/35'}`}>
      <div className="flex items-start gap-3">
        <span className={`grid h-10 w-16 shrink-0 place-items-center rounded border text-[11px] font-semibold ${memoryKindTone(mainKind)}`}>
          {memoryKindLabel(mainKind)}
        </span>
        <div className="min-w-0 flex-1">
          <button
            onClick={() => onOpen(item)}
            className="block max-w-full truncate text-left text-sm font-semibold text-ops-text hover:text-ops-accent"
            title={item.path}
          >
            {item.path}
          </button>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-ops-overlay">
            <span>{scopeLabel}作用域：{item.scope_id}</span>
            <span>{item.entries} 条</span>
            <span>{formatMemorySize(item.size)}</span>
            <span>{item.updated_at}</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <span className={`rounded-full border px-2 py-0.5 text-[10px] ${item.retrieval_enabled === false ? 'border-amber-300/35 text-amber-200' : 'border-ops-success/35 text-ops-success'}`}>
              {memoryUsageLabel(item)}
            </span>
            {memoryKindChips(item).slice(0, 4).map((chip) => (
              <span key={chip.kind} className={`rounded-full border px-2 py-0.5 text-[10px] ${memoryKindTone(chip.kind)}`}>
                {chip.label} {chip.count}
              </span>
            ))}
          </div>
          {item.preview && (
            <p className="mt-2 line-clamp-2 text-xs leading-5 text-ops-subtext">{item.preview}</p>
          )}
        </div>
        <button
          onClick={() => onDelete(item)}
          className="rounded-lg px-2 py-1 text-xs text-ops-overlay transition-colors hover:bg-ops-alert/10 hover:text-ops-alert"
        >
          删除
        </button>
      </div>
    </article>
  )
}

export function MemoryDetailPanel({
  draft,
  exporting,
  memory,
  saving,
  onDraftChange,
  onExport,
  onSave,
}: {
  draft: string
  exporting: boolean
  memory: MemoryDetail | null
  saving: boolean
  onDraftChange: (value: string) => void
  onExport: () => void
  onSave: () => void
}) {
  if (!memory) {
    return (
      <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-5">
        <div className="text-sm font-semibold text-ops-text">选择一条 AI 记忆</div>
        <p className="mt-2 text-sm leading-6 text-ops-subtext">
          这里展示 Claude 风格文件记忆的完整内容。它们是历史经验，不是系统指令，AI 使用前必须结合当前资产实时验证。
        </p>
      </section>
    )
  }
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60">
      <div className="border-b border-ops-surface0 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-xs font-semibold text-ops-accent">记忆详情</div>
            <h2 className="mt-1 break-all text-sm font-bold text-ops-text">{memory.path}</h2>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              onClick={onExport}
              disabled={exporting}
              className="rounded-lg border border-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent disabled:opacity-50"
            >
              {exporting ? '导出中...' : '导出全部'}
            </button>
            <button
              onClick={onSave}
              disabled={saving || memory.access === 'read_only'}
              className="rounded-lg bg-ops-accent px-3 py-1.5 text-xs font-semibold text-ops-dark disabled:opacity-50"
              title={memory.access === 'read_only' ? '只读记忆库不能编辑' : '保存记忆'}
            >
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-ops-overlay">
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5">{memory.store_name || memory.scope_id}</span>
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5">{memory.access === 'read_only' ? '只读' : '可写'}</span>
          <span className={`rounded-full border px-2 py-0.5 ${memory.retrieval_enabled === false ? 'border-amber-300/35 text-amber-200' : 'border-ops-success/35 text-ops-success'}`}>
            {memoryUsageLabel(memory)}
          </span>
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5">{formatMemorySize(memory.size)}</span>
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5">{memory.updated_at}</span>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {memoryKindChips(memory).slice(0, 6).map((chip) => (
            <span key={chip.kind} className={`rounded-full border px-2 py-0.5 text-[10px] ${memoryKindTone(chip.kind)}`}>
              {chip.label} {chip.count}
            </span>
          ))}
        </div>
      </div>
      <textarea
        value={draft}
        onChange={(event) => onDraftChange(event.target.value)}
        readOnly={memory.access === 'read_only'}
        className="min-h-[420px] w-full resize-y bg-transparent p-4 font-mono text-xs leading-5 text-ops-subtext outline-none read-only:opacity-80"
      />
    </section>
  )
}

export function MemoryCreatePanel({
  creating,
  scope,
  summary,
  onCreate,
  onScopeChange,
  onSummaryChange,
}: {
  creating: boolean
  scope: string
  summary: string
  onCreate: () => void
  onScopeChange: (value: string) => void
  onSummaryChange: (value: string) => void
}) {
  return (
    <section className="rounded-lg border border-ops-accent/30 bg-ops-accent/5 p-4">
      <div className="text-sm font-semibold text-ops-text">新建 AI 记忆</div>
      <p className="mt-1 text-xs leading-5 text-ops-subtext">
        手工写入当前会话明确规则、用户偏好或已验证经验。默认作用域就是当前 session，不建议写 manual、asset-host 或 asset-kind，避免串到其他会话。
      </p>
      <input
        value={scope}
        onChange={(event) => onScopeChange(event.target.value)}
        className="mt-3 h-9 w-full rounded-md border border-ops-surface1 bg-ops-panel/70 px-3 text-xs text-ops-text outline-none placeholder:text-ops-overlay focus:border-ops-accent/60"
        placeholder="当前会话 ID，例如 5b39e8cc-..."
      />
      <textarea
        value={summary}
        onChange={(event) => onSummaryChange(event.target.value)}
        className="mt-2 min-h-28 w-full resize-y rounded-md border border-ops-surface1 bg-ops-panel/70 px-3 py-2 text-xs leading-5 text-ops-text outline-none placeholder:text-ops-overlay focus:border-ops-accent/60"
        placeholder="写入当前会话要保留的核心记忆，最好包含：记忆类型、可信度、保留方式、使用提醒。"
      />
      <button
        onClick={onCreate}
        disabled={creating || !scope.trim() || !summary.trim()}
        className="mt-2 rounded-lg bg-ops-accent px-3 py-1.5 text-xs font-semibold text-ops-dark disabled:opacity-50"
      >
        {creating ? '创建中...' : '创建记忆'}
      </button>
    </section>
  )
}

export function MemorySearchPanel({
  query,
  results,
  scopes,
  searching,
  onQueryChange,
  onScopesChange,
  onSearch,
}: {
  query: string
  results: MemorySearchResult[]
  scopes: string
  searching: boolean
  onQueryChange: (value: string) => void
  onScopesChange: (value: string) => void
  onSearch: () => void
}) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="text-sm font-semibold text-ops-text">记忆检索预览</div>
      <p className="mt-1 text-xs leading-5 text-ops-subtext">
        输入问题后先预览当前 session 会命中的记忆，用来检查“AI 为什么想起这条经验”。审计归档不会自动召回。
      </p>
      <input
        value={scopes}
        onChange={(event) => onScopesChange(event.target.value)}
        className="mt-3 h-9 w-full rounded-md border border-ops-surface1 bg-ops-panel/70 px-3 text-xs text-ops-text outline-none placeholder:text-ops-overlay focus:border-ops-accent/60"
        placeholder="当前会话 ID，多个用逗号分隔"
      />
      <textarea
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        className="mt-2 min-h-20 w-full resize-y rounded-md border border-ops-surface1 bg-ops-panel/70 px-3 py-2 text-xs leading-5 text-ops-text outline-none placeholder:text-ops-overlay focus:border-ops-accent/60"
        placeholder="例如：SSH 高频登录是不是本地程序造成的？"
      />
      <button
        onClick={onSearch}
        disabled={searching || !query.trim() || !scopes.trim()}
        className="mt-2 rounded-lg border border-ops-accent/45 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10 disabled:opacity-50"
      >
        {searching ? '检索中...' : '预览命中记忆'}
      </button>
      <div className="mt-3 space-y-2">
        {results.length > 0 ? results.map((item, index) => (
          <article key={`${item.path || item.session_id || 'memory'}-${index}`} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
            <div className="flex items-center justify-between gap-2 text-[11px] text-ops-overlay">
              <span className="truncate">{item._memory_scope_id || item.session_id || item.path || 'unknown'}</span>
              <span>{item.timestamp || '无时间'}</span>
            </div>
            <div className="mt-1 flex flex-wrap gap-1.5">
              <span className={`rounded-full border px-2 py-0.5 text-[10px] ${memoryKindTone(item.memory_kind)}`}>
                {memoryKindLabel(item.memory_kind, item.memory_kind_label)}
              </span>
              <span className="rounded-full border border-ops-success/30 px-2 py-0.5 text-[10px] text-ops-success">
                {item.retrieval_enabled === false ? '仅审计' : '会进入上下文'}
              </span>
              {item.usage_role && (
                <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-overlay">
                  {item.usage_role}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs leading-5 text-ops-subtext">{item.summary || '该记忆没有摘要内容'}</p>
            {typeof item._distance === 'number' && (
              <div className="mt-1 font-mono text-[11px] text-ops-overlay">距离 {item._distance.toFixed(4)}</div>
            )}
          </article>
        )) : (
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-4 text-center text-xs text-ops-overlay">
            暂无检索结果
          </div>
        )}
      </div>
    </section>
  )
}

export function MemoryPendingConflictsPanel({
  items,
  resolvingKey,
  onOpen,
  onResolve,
}: {
  items: MemoryPendingConflict[]
  resolvingKey: string | null
  onOpen: (path: string) => void
  onResolve: (item: MemoryPendingConflict, action: 'accept_new' | 'keep_old' | 'merged') => void
}) {
  return (
    <section className="rounded-lg border border-ops-accent/30 bg-ops-accent/5 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">待确认记忆</div>
          <p className="mt-1 text-xs text-ops-subtext">新旧记忆存在冲突时先进入这里，由你决定是否采纳。</p>
        </div>
        <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-xs text-ops-accent">
          {items.length}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => (
          <article key={item.version_id} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
            <div className="flex items-start justify-between gap-2">
              <button
                onClick={() => onOpen(item.path)}
                className="min-w-0 truncate text-left text-xs font-semibold text-ops-accent hover:text-ops-text"
                title={item.path}
              >
                {item.path}
              </button>
              <span className="shrink-0 font-mono text-[11px] text-ops-overlay">{item.timestamp}</span>
            </div>
            <p className="mt-1 text-xs leading-5 text-ops-subtext">{item.reason}</p>
            {item.existing_preview && (
              <div className="mt-2 rounded border border-ops-alert/20 bg-ops-alert/5 px-2 py-1 text-[11px] leading-5 text-ops-subtext">
                旧记忆：{item.existing_preview}
              </div>
            )}
            {item.new_preview && (
              <div className="mt-1 rounded border border-ops-success/20 bg-ops-success/5 px-2 py-1 text-[11px] leading-5 text-ops-subtext">
                新记忆：{item.new_preview}
              </div>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              {([
                ['accept_new', '采纳新记忆'],
                ['keep_old', '保留旧记忆'],
                ['merged', '已手动合并'],
              ] as const).map(([action, label]) => {
                const busy = resolvingKey === `${item.version_id}:${action}`
                return (
                  <button
                    key={action}
                    onClick={() => onResolve(item, action)}
                    disabled={Boolean(resolvingKey)}
                    className="rounded border border-ops-surface0 px-2 py-1 text-[11px] text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent disabled:opacity-50"
                  >
                    {busy ? '处理中...' : label}
                  </button>
                )
              })}
            </div>
          </article>
        )) : (
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-4 text-center text-xs text-ops-overlay">
            暂无待确认冲突
          </div>
        )}
      </div>
    </section>
  )
}

function learningCandidateStatusActions(status: string): Array<{ status: LearningCandidateStatus; label: string; reason: string }> {
  if (status === 'draft') {
    return [{ status: 'reviewing', label: '提交评审', reason: '候选内容已整理，提交人工评审。' }]
  }
  if (status === 'reviewing') {
    return [
      { status: 'approved', label: '批准', reason: '人工评审通过，允许进入发布准备。' },
      { status: 'rejected', label: '拒绝', reason: '人工评审未通过，退回候选池保留审计。' },
    ]
  }
  if (status === 'approved') {
    return [{ status: 'published', label: '标记发布', reason: '候选已完成发布或已接入对应 Runbook/Skill。' }]
  }
  return []
}

function latestLearningCandidateEvent(item: LearningCandidate) {
  const events = item.status_events || []
  return events.length > 0 ? events[events.length - 1] : null
}

type LearningCandidateChecklist = NonNullable<LearningCandidate['quality_checklist']>

function learningCandidateChecklist(item: LearningCandidate) {
  const fallback = [
    { key: 'source_message', label: '来源消息', ok: Boolean(item.source_session_id && item.feedback_target_message_id !== undefined) },
    { key: 'tool_evidence', label: '工具证据', ok: Boolean(item.evidence_refs?.length) },
    { key: 'scope', label: '适用范围', ok: false },
    { key: item.target_type === 'runbook' ? 'steps' : 'inputs', label: item.target_type === 'runbook' ? '执行步骤' : '输入参数', ok: false },
    { key: 'risk_boundary', label: '风险边界', ok: false },
    { key: item.target_type === 'runbook' ? 'verification' : 'tests', label: item.target_type === 'runbook' ? '验证项' : '测试项', ok: false },
    { key: 'rollback', label: '回滚方案', ok: false },
  ]
  return item.quality_checklist?.length ? item.quality_checklist : fallback
}

function learningCandidateQualityReady(item: LearningCandidate) {
  const checklist = learningCandidateChecklist(item)
  return checklist.length > 0 && checklist.every((row) => row.ok)
}

function learningCandidateActionBlocked(item: LearningCandidate, status: LearningCandidateStatus) {
  return (status === 'approved' || status === 'published') && !learningCandidateQualityReady(item)
}

export function MemoryCandidatesPanel({
  items,
  learningCandidates,
  reviewingPath,
  updatingLearningCandidate,
  onOpen,
  onConfirm,
  onConvert,
  onOpenEvidence,
  onFocusMessage,
  onUpdateLearningQuality,
  onUpdateLearningStatus,
  onReject,
  onOpenLearningCandidateArtifact,
  readingLearningCandidateArtifact,
}: {
  items: MemoryCandidate[]
  learningCandidates: LearningCandidate[]
  reviewingPath: string | null
  updatingLearningCandidate: string | null
  onOpen: (path: string) => void
  onConfirm: (item: MemoryCandidate) => void
  onConvert: (item: MemoryCandidate, action: Extract<MemoryCandidateAction, 'to_runbook' | 'to_skill'>) => void
  onOpenEvidence: (item: MemoryCandidate, ref: MemoryCandidateRef) => void
  onFocusMessage: (item: MemoryCandidate) => void
  onUpdateLearningQuality: (item: LearningCandidate, checklist: LearningCandidateChecklist, reason: string) => void
  onUpdateLearningStatus: (item: LearningCandidate, status: LearningCandidateStatus, reason: string) => void
  onReject: (item: MemoryCandidate) => void
  onOpenLearningCandidateArtifact: (item: LearningCandidate) => void
  readingLearningCandidateArtifact?: string | null
}) {
  const [learningDetail, setLearningDetail] = useState<LearningCandidate | null>(null)
  const groupedItems = [
    {
      key: 'pending',
      title: '待确认候选',
      hint: '可以确认沉淀、转 Runbook、转 Skill 或拒绝。',
      items: items.filter((item) => (item.review_status || 'pending') === 'pending'),
      tone: 'border-ops-success/30 bg-ops-success/5',
      badge: 'border-ops-success/35 text-ops-success',
    },
    {
      key: 'runbook_candidate',
      title: 'Runbook 候选',
      hint: '已从成功经验分流，等待人工整理成可复用运维流程。',
      items: items.filter((item) => item.review_status === 'runbook_candidate'),
      tone: 'border-ops-accent/25 bg-ops-accent/5',
      badge: 'border-ops-accent/35 text-ops-accent',
    },
    {
      key: 'skill_candidate',
      title: 'Skill 候选',
      hint: '已从成功经验分流，等待整理、校验并进入技能体系。',
      items: items.filter((item) => item.review_status === 'skill_candidate'),
      tone: 'border-sky-300/25 bg-sky-300/5',
      badge: 'border-sky-300/35 text-sky-200',
    },
  ]
  return (
    <section className="rounded-lg border border-ops-success/30 bg-ops-success/5 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">学习候选</div>
          <p className="mt-1 text-xs text-ops-subtext">点赞、成功路径和后续 Runbook/Skill 候选先进入这里，确认后才进入可检索记忆。</p>
        </div>
        <span className="rounded-full border border-ops-success/35 px-2 py-0.5 text-xs text-ops-success">
          {items.length}
        </span>
      </div>
      <div className="mt-3 space-y-3">
        {items.length > 0 ? groupedItems.map((group) => (
          <div key={group.key} className={`rounded-lg border ${group.tone} p-3`}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="text-xs font-semibold text-ops-text">{group.title}</div>
                <p className="mt-1 text-[11px] leading-5 text-ops-subtext">{group.hint}</p>
              </div>
              <span className={`rounded-full border px-2 py-0.5 text-[10px] ${group.badge}`}>
                {group.items.length}
              </span>
            </div>
            <div className="mt-2 space-y-2">
              {group.items.length > 0 ? group.items.map((item, index) => {
                const busy = reviewingPath === item.candidate_id
                const actionable = (item.review_status || 'pending') === 'pending'
                return (
            <article key={item.candidate_id || `${item.path}-${item.timestamp}-${index}`} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                <span className="rounded-full border border-ops-success/35 px-2 py-0.5 text-ops-success">
                  {item.memory_kind_label || '候选记忆'}
                </span>
                <span className="rounded-full border border-amber-300/35 px-2 py-0.5 text-amber-200">
                  {item.review_status || 'pending'}
                </span>
                <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-overlay">
                  {item.candidate_type || 'memory_candidate'}
                </span>
                <span className="font-mono text-ops-overlay">{item.timestamp || '-'}</span>
                <span className="font-mono text-ops-overlay">{item.candidate_id}</span>
                {item.feedback_target_message_id !== undefined && (
                  <span className="font-mono text-ops-overlay">消息 {item.feedback_target_message_id}</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => onOpen(item.path)}
                className="mt-2 block max-w-full truncate text-left text-xs font-semibold text-ops-accent hover:text-ops-text"
                title={item.path}
              >
                {item.path}
              </button>
              <p className="mt-1 line-clamp-3 text-xs leading-5 text-ops-subtext">
                {item.summary_preview || item.summary || '该候选暂无摘要'}
              </p>
              <p className="mt-2 text-[11px] leading-5 text-ops-overlay">
                {item.recommended_action || '确认前不会进入模型检索上下文。'}
              </p>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                <div className="rounded border border-ops-surface0 bg-ops-dark/30 px-2 py-1.5">
                  <div className="text-[11px] font-semibold text-ops-text">来源链</div>
                  <div className="mt-1 space-y-1">
                    {(item.source_refs || []).length > 0 ? item.source_refs?.slice(0, 4).map((ref, refIndex) => (
                      <div key={`${item.candidate_id}-source-${refIndex}`} className="truncate font-mono text-[11px] text-ops-overlay" title={ref.path || ref.id || ref.tool || ''}>
                        {ref.label || ref.type || 'source'}: {ref.id || ref.path || ref.tool || '-'}
                      </div>
                    )) : (
                      <div className="text-[11px] text-ops-overlay">仅保留记忆文件路径</div>
                    )}
                  </div>
                </div>
                <div className="rounded border border-ops-surface0 bg-ops-dark/30 px-2 py-1.5">
                  <div className="text-[11px] font-semibold text-ops-text">工具证据</div>
                  <div className="mt-1 space-y-1">
                    {(item.evidence_refs || []).length > 0 ? item.evidence_refs?.slice(0, 4).map((ref, refIndex) => (
                      <button
                        key={`${item.candidate_id}-evidence-${refIndex}`}
                        type="button"
                        onClick={() => onOpenEvidence(item, ref)}
                        className="block max-w-full truncate text-left font-mono text-[11px] text-ops-accent hover:text-ops-text"
                        title={[ref.id || ref.tool || '', candidateEvidenceActionText(ref)].filter(Boolean).join(' · ')}
                      >
                        {ref.id || ref.tool || ref.type || '-'}{ref.status ? ` · ${ref.status}` : ''}
                        {candidateEvidenceActionText(ref) ? ` · ${candidateEvidenceActionText(ref)}` : ''}
                      </button>
                    )) : (
                      <div className="text-[11px] text-ops-overlay">暂无工具证据绑定</div>
                    )}
                  </div>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {actionable && (
                  <>
                    <button
                      type="button"
                      onClick={() => onConfirm(item)}
                      disabled={Boolean(reviewingPath)}
                      className="rounded border border-ops-success/40 px-2 py-1 text-[11px] font-semibold text-ops-success hover:bg-ops-success/10 disabled:opacity-50"
                    >
                      {busy ? '确认中...' : '确认沉淀'}
                    </button>
                    <button
                      type="button"
                      onClick={() => onConvert(item, 'to_runbook')}
                      disabled={Boolean(reviewingPath)}
                      className="rounded border border-ops-accent/35 px-2 py-1 text-[11px] font-semibold text-ops-accent hover:bg-ops-accent/10 disabled:opacity-50"
                    >
                      {busy ? '处理中...' : '转 Runbook'}
                    </button>
                    <button
                      type="button"
                      onClick={() => onConvert(item, 'to_skill')}
                      disabled={Boolean(reviewingPath)}
                      className="rounded border border-sky-300/35 px-2 py-1 text-[11px] font-semibold text-sky-200 hover:bg-sky-300/10 disabled:opacity-50"
                    >
                      {busy ? '处理中...' : '转 Skill'}
                    </button>
                    <button
                      type="button"
                      onClick={() => onReject(item)}
                      disabled={Boolean(reviewingPath)}
                      className="rounded border border-ops-alert/35 px-2 py-1 text-[11px] font-semibold text-ops-alert hover:bg-ops-alert/10 disabled:opacity-50"
                    >
                      {busy ? '处理中...' : '拒绝候选'}
                    </button>
                  </>
                )}
                <button
                  type="button"
                  onClick={() => onOpen(item.path)}
                  className="rounded border border-ops-surface0 px-2 py-1 text-[11px] text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
                >
                  打开记忆文件
                </button>
                {item.feedback_target_message_id !== undefined ? (
                  <button
                    type="button"
                    onClick={() => onFocusMessage(item)}
                    className="rounded border border-ops-surface0 px-2 py-1 text-[11px] text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
                  >
                    定位消息
                  </button>
                ) : null}
              </div>
            </article>
                )
              }) : (
                <div className="rounded-md border border-ops-surface0 bg-ops-dark/25 px-3 py-3 text-center text-[11px] text-ops-overlay">
                  暂无{group.title}
                </div>
              )}
            </div>
          </div>
        )) : (
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-4 text-center text-xs text-ops-overlay">
            暂无待确认学习候选
          </div>
        )}
      </div>
      <div className="mt-3 rounded-lg border border-ops-surface0 bg-ops-dark/25 p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="text-xs font-semibold text-ops-text">发布候选池</div>
            <p className="mt-1 text-[11px] leading-5 text-ops-subtext">
              这里是已从记忆候选分流出来的 Runbook/Skill 生命周期对象，后续用于审批、发布和版本记录。
            </p>
          </div>
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-overlay">
            {learningCandidates.length}
          </span>
        </div>
        <div className="mt-2 grid gap-2 xl:grid-cols-2">
          {learningCandidates.length > 0 ? learningCandidates.slice(0, 8).map((item) => {
            const latestEvent = latestLearningCandidateEvent(item)
            const publishedArtifact = item.published_artifact
            return (
            <article key={item.id} className="rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2">
              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                <span className={`rounded-full border px-2 py-0.5 ${item.target_type === 'runbook' ? 'border-ops-accent/35 text-ops-accent' : 'border-sky-300/35 text-sky-200'}`}>
                  {item.target_type === 'runbook' ? 'Runbook' : 'Skill'}
                </span>
                <span className="rounded-full border border-amber-300/35 px-2 py-0.5 text-amber-200">
                  {item.status || 'draft'}
                </span>
                <span className="font-mono text-ops-overlay">{item.created_at || '-'}</span>
              </div>
              <div className="mt-2 truncate font-mono text-[11px] text-ops-overlay" title={item.id}>
                {item.id}
              </div>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-ops-subtext">
                {item.summary_preview || item.summary || '暂无摘要'}
              </p>
              {publishedArtifact ? (
                <div className="mt-2 rounded-md border border-emerald-300/35 bg-emerald-300/8 px-2 py-2 text-[10px] text-ops-overlay">
                  <div className="font-semibold text-emerald-200">发布草稿已生成</div>
                  <div>草稿ID：{publishedArtifact.artifact_id}</div>
                  <div>状态：{publishedArtifact.status}</div>
                  <div>路径：{publishedArtifact.file_path}</div>
                  <div>更新时间：{publishedArtifact.generated_at}</div>
                  <p className="mt-1 whitespace-pre-wrap text-ops-overlay">{publishedArtifact.content_preview || '无内容预览'}</p>
                </div>
              ) : (
                item.status === 'published'
                  ? <div className="mt-2 text-[10px] text-ops-overlay">发布状态已更新，但草稿信息暂未生成。</div>
                  : null
              )}
              <p className="mt-2 text-[11px] leading-5 text-ops-overlay">
                {item.next_action || '等待人工整理和发布。'}
              </p>
              <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-ops-overlay">
                {item.source_session_id && <span>会话 {item.source_session_id}</span>}
                {item.evidence_refs?.length ? <span>证据 {item.evidence_refs.length}</span> : <span>无证据引用</span>}
                <span className="truncate">来源 {item.source_path}</span>
              </div>
              {latestEvent && (
                <div className="mt-2 truncate text-[10px] text-ops-overlay" title={latestEvent.reason || ''}>
                  最近状态：{latestEvent.from || 'new'} → {latestEvent.to} · {latestEvent.actor}
                </div>
              )}
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setLearningDetail(item)}
                  className="rounded border border-ops-surface0 px-2 py-1 text-[11px] font-semibold text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
                >
                  查看详情
                </button>
                {learningCandidateStatusActions(item.status || 'draft').map((action) => (
                  <button
                    key={`${item.id}-${action.status}`}
                    type="button"
                    onClick={() => onUpdateLearningStatus(item, action.status, action.reason)}
                    disabled={updatingLearningCandidate === item.id || learningCandidateActionBlocked(item, action.status)}
                    title={learningCandidateActionBlocked(item, action.status) ? '需先补齐并保存发布前质量清单' : action.reason}
                    className="rounded border border-ops-accent/35 px-2 py-1 text-[11px] font-semibold text-ops-accent hover:bg-ops-accent/10 disabled:opacity-50"
                  >
                    {updatingLearningCandidate === item.id
                      ? '更新中...'
                      : learningCandidateActionBlocked(item, action.status)
                        ? '需补齐清单'
                        : action.label}
                  </button>
                ))}
                {publishedArtifact ? (
                  <button
                    type="button"
                    onClick={() => onOpenLearningCandidateArtifact(item)}
                    disabled={Boolean(readingLearningCandidateArtifact)}
                    className="rounded border border-emerald-300/35 px-2 py-1 text-[11px] font-semibold text-emerald-200 hover:bg-emerald-300/10 disabled:opacity-50"
                  >
                    {readingLearningCandidateArtifact === item.id ? '读取中...' : '打开发布草稿'}
                  </button>
                ) : null}
              </div>
            </article>
          )}) : (
            <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-4 text-center text-xs text-ops-overlay xl:col-span-2">
              暂无发布候选。把学习候选转为 Runbook 或 Skill 后会进入这里。
            </div>
          )}
        </div>
      </div>
      <LearningCandidateDetailDrawer
        key={learningDetail?.id || 'none'}
        item={learningDetail}
        saving={Boolean(learningDetail && updatingLearningCandidate === learningDetail.id)}
        onClose={() => setLearningDetail(null)}
        onSave={onUpdateLearningQuality}
      />
    </section>
  )
}

function LearningCandidateDetailDrawer({
  item,
  saving,
  onClose,
  onSave,
}: {
  item: LearningCandidate | null
  saving: boolean
  onClose: () => void
  onSave: (item: LearningCandidate, checklist: LearningCandidateChecklist, reason: string) => void
}) {
  if (!item) return null
  return (
    <LearningCandidateDetailContent
      item={item}
      saving={saving}
      onClose={onClose}
      onSave={onSave}
    />
  )
}

function LearningCandidateDetailContent({
  item,
  saving,
  onClose,
  onSave,
}: {
  item: LearningCandidate
  saving: boolean
  onClose: () => void
  onSave: (item: LearningCandidate, checklist: LearningCandidateChecklist, reason: string) => void
}) {
  const checklist = learningCandidateChecklist(item)
  const [draftChecklist, setDraftChecklist] = useState<LearningCandidateChecklist>(checklist)
  const [qualityReason, setQualityReason] = useState('补齐发布前质量清单。')
  const passed = checklist.filter((row) => row.ok).length
  const draftPassed = draftChecklist.filter((row) => row.ok).length
  const updateChecklistRow = (key: string, patch: Partial<LearningCandidateChecklist[number]>) => {
    setDraftChecklist((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)))
  }
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50" onClick={onClose}>
      <aside
        className="h-full w-full max-w-2xl overflow-y-auto border-l border-ops-surface1 bg-ops-panel p-5 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-ops-text">发布候选详情</div>
            <div className="mt-1 font-mono text-[11px] text-ops-overlay">{item.id}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
          >
            关闭
          </button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-[11px]">
          <span className={`rounded-full border px-2 py-0.5 ${item.target_type === 'runbook' ? 'border-ops-accent/35 text-ops-accent' : 'border-sky-300/35 text-sky-200'}`}>
            {item.target_type === 'runbook' ? 'Runbook' : 'Skill'}
          </span>
          <span className="rounded-full border border-amber-300/35 px-2 py-0.5 text-amber-200">{item.status || 'draft'}</span>
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-overlay">{item.created_at}</span>
        </div>
        <section className="mt-4 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-3">
          <div className="text-xs font-semibold text-ops-text">候选摘要</div>
          <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-ops-subtext">{item.summary || '暂无摘要'}</p>
        </section>
        <section className="mt-3 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-3">
          <div className="text-xs font-semibold text-ops-text">发布草稿</div>
          {item.published_artifact ? (
            <div className="mt-2 space-y-1 text-[11px] text-ops-subtext">
              <CandidateEvidenceInfoLine label="草稿ID" value={item.published_artifact.artifact_id} />
              <CandidateEvidenceInfoLine label="目标类型" value={item.published_artifact.target_type} />
              <CandidateEvidenceInfoLine label="文件路径" value={item.published_artifact.file_path} />
              <CandidateEvidenceInfoLine label="草稿状态" value={item.published_artifact.status} />
              <CandidateEvidenceInfoLine label="生成时间" value={item.published_artifact.generated_at} />
              <CandidateEvidenceInfoLine label="生成原因" value={item.published_artifact.generated_reason || '-'} />
              <CandidateEvidenceInfoLine label="生成者" value={item.published_artifact.generated_by || '-'} />
              {item.published_artifact.content_preview && (
                <div className="rounded border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
                  <div className="text-[11px] text-ops-overlay">草稿预览</div>
                  <div className="mt-1 whitespace-pre-wrap text-xs text-ops-subtext">
                    {item.published_artifact.content_preview}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="mt-2 rounded border border-ops-surface0 bg-ops-dark/35 px-3 py-2 text-xs text-ops-overlay">尚未生成发布草稿。标记为 Published 后自动创建。</div>
          )}
        </section>
        <section className="mt-3 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs font-semibold text-ops-text">发布前质量清单</div>
            <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-overlay">
              {draftPassed}/{draftChecklist.length}
            </span>
          </div>
          <div className="mt-2 space-y-2">
            {draftChecklist.map((row) => (
              <div key={row.key} className={`rounded border px-2 py-2 text-[11px] ${row.ok ? 'border-ops-success/35 bg-ops-success/5 text-ops-success' : 'border-amber-300/35 bg-amber-300/5 text-amber-200'}`}>
                <label className="flex items-center gap-2 font-semibold">
                  <input
                    type="checkbox"
                    checked={row.ok}
                    onChange={(event) => updateChecklistRow(row.key, { ok: event.target.checked })}
                    className="h-3.5 w-3.5 accent-emerald-400"
                  />
                  <span>{row.ok ? '已具备' : '待补齐'} · {row.label}</span>
                </label>
                <input
                  value={row.note || ''}
                  onChange={(event) => updateChecklistRow(row.key, { note: event.target.value })}
                  placeholder="补充依据、验证方法或待办说明"
                  className="mt-2 w-full rounded border border-ops-surface0 bg-ops-dark/45 px-2 py-1.5 text-[11px] text-ops-subtext outline-none focus:border-ops-accent/60"
                />
              </div>
            ))}
          </div>
          <div className="mt-3">
            <label className="text-[11px] font-semibold text-ops-text">保存理由</label>
            <input
              value={qualityReason}
              onChange={(event) => setQualityReason(event.target.value)}
              className="mt-1 w-full rounded border border-ops-surface0 bg-ops-dark/45 px-2 py-1.5 text-xs text-ops-subtext outline-none focus:border-ops-accent/60"
            />
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <div className="text-[11px] text-ops-overlay">
              原始完成度 {passed}/{checklist.length}，当前编辑 {draftPassed}/{draftChecklist.length}
            </div>
            <button
              type="button"
              onClick={() => onSave(item, draftChecklist, qualityReason.trim() || '更新发布前质量清单。')}
              disabled={saving}
              className="rounded border border-ops-accent/40 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10 disabled:opacity-50"
            >
              {saving ? '保存中...' : '保存质量清单'}
            </button>
          </div>
        </section>
        <section className="mt-3 grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/30 p-3">
            <div className="text-xs font-semibold text-ops-text">来源链</div>
            <div className="mt-2 space-y-1">
              {(item.source_refs || []).length > 0 ? item.source_refs?.map((ref, index) => (
                <div key={`${item.id}-source-${index}`} className="truncate font-mono text-[11px] text-ops-overlay" title={ref.path || ref.id || ref.tool || ''}>
                  {ref.label || ref.type || 'source'}: {ref.id || ref.path || ref.tool || '-'}
                </div>
              )) : (
                <div className="text-[11px] text-ops-overlay">暂无来源链</div>
              )}
            </div>
          </div>
          <div className="rounded-lg border border-ops-surface0 bg-ops-dark/30 p-3">
            <div className="text-xs font-semibold text-ops-text">工具证据</div>
            <div className="mt-2 space-y-1">
              {(item.evidence_refs || []).length > 0 ? item.evidence_refs?.map((ref, index) => (
                <div
                  key={`${item.id}-evidence-${index}`}
                  className="truncate font-mono text-[11px] text-ops-overlay"
                  title={[ref.id || ref.tool || '', candidateEvidenceActionText(ref)].filter(Boolean).join(' · ')}
                >
                  {ref.id || ref.tool || ref.type || '-'}{ref.status ? ` · ${ref.status}` : ''}
                  {candidateEvidenceActionText(ref) ? ` · ${candidateEvidenceActionText(ref)}` : ''}
                </div>
              )) : (
                <div className="text-[11px] text-ops-overlay">暂无工具证据</div>
              )}
            </div>
          </div>
        </section>
        <section className="mt-3 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-3">
          <div className="text-xs font-semibold text-ops-text">状态流</div>
          <div className="mt-2 space-y-2">
            {(item.status_events || []).length > 0 ? item.status_events?.map((event, index) => (
              <div key={`${item.id}-event-${index}`} className="rounded border border-ops-surface0 bg-ops-panel/40 px-2 py-1.5 text-[11px] text-ops-subtext">
                <div>{event.from || 'new'} → {event.to} · {event.actor} · {event.timestamp}</div>
                <div className="mt-1 text-ops-overlay">{event.reason}</div>
              </div>
            )) : (
              <div className="text-[11px] text-ops-overlay">暂无状态事件</div>
            )}
          </div>
        </section>
      </aside>
    </div>
  )
}

export function LearningCandidatePublishArtifactDialog({
  artifact,
  reading,
  onCopy,
  onDownload,
  onClose,
}: {
  artifact: LearningCandidatePublishedArtifactDetail | null
  reading: boolean
  onCopy: () => void
  onDownload: () => void
  onClose: () => void
}) {
  if (!artifact) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <section className="flex h-[88vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-ops-surface1 bg-ops-panel shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-ops-surface0 px-4 py-3">
          <div>
            <div className="text-sm font-semibold text-ops-text">发布候选草稿</div>
            <div className="mt-1 font-mono text-[11px] text-ops-overlay">
              {artifact.candidate_id} / {artifact.artifact_id}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-ops-surface0 px-2 py-1 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
          >
            关闭
          </button>
        </div>
        <div className="max-h-[78vh] overflow-y-auto p-4">
          {reading && (
            <div className="mb-2 rounded border border-ops-accent/35 bg-ops-accent/10 px-3 py-2 text-xs text-ops-accent">
              正在读取发布草稿...
            </div>
          )}
          <div className="grid gap-2 md:grid-cols-2">
            <CandidateEvidenceInfoLine label="草稿ID" value={artifact.artifact_id} />
            <CandidateEvidenceInfoLine label="目标类型" value={artifact.target_type} />
            <CandidateEvidenceInfoLine label="文件路径" value={artifact.file_path} />
            <CandidateEvidenceInfoLine label="草稿状态" value={artifact.status} />
            <CandidateEvidenceInfoLine label="生成时间" value={artifact.generated_at} />
            <CandidateEvidenceInfoLine label="生成原因" value={artifact.generated_reason || '-'} />
            <CandidateEvidenceInfoLine label="生成者" value={artifact.generated_by || '-'} />
            <CandidateEvidenceInfoLine label="内容摘要" value={artifact.content_preview || '无内容预览'} />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onCopy}
              className="rounded border border-ops-accent/35 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent/10"
            >
              复制全部内容
            </button>
            <button
              type="button"
              onClick={onDownload}
              className="rounded border border-emerald-300/35 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-300/10"
            >
              下载 Markdown
            </button>
          </div>
          <pre className="mt-3 max-h-[52vh] overflow-auto rounded-md border border-ops-surface0 bg-ops-dark p-3 text-xs leading-6 whitespace-pre-wrap text-ops-subtext">
            {artifact.content}
          </pre>
        </div>
      </section>
    </div>
  )
}

export interface MemoryCandidateEvidenceDetail {
  candidate: MemoryCandidate
  ref: MemoryCandidateRef
  trace?: ExecTraceItem | null
  sessionMode?: 'readonly' | 'readwrite'
  loading?: boolean
  error?: string
}

export function MemoryCandidateEvidenceDialog({
  detail,
  onClose,
  sessionMode,
}: {
  detail: MemoryCandidateEvidenceDetail | null
  onClose: () => void
  sessionMode?: 'readonly' | 'readwrite'
}) {
  if (!detail) return null
  const trace = detail.trace || null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <section className="max-h-[88vh] w-full max-w-3xl overflow-hidden rounded-xl border border-ops-surface1 bg-ops-panel shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-ops-surface0 px-4 py-3">
          <div>
            <div className="text-sm font-semibold text-ops-text">工具证据详情</div>
            <div className="mt-1 font-mono text-[11px] text-ops-overlay">
              {detail.ref.id || detail.ref.tool || detail.ref.type || '-'}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-ops-surface0 px-2 py-1 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
          >
            关闭
          </button>
        </div>
        <div className="max-h-[72vh] overflow-y-auto p-4">
          <div className="grid gap-2 md:grid-cols-2">
            <CandidateEvidenceInfoLine label="候选" value={detail.candidate.candidate_id} />
            <CandidateEvidenceInfoLine label="来源会话" value={detail.candidate.source_session_id || '-'} />
            <CandidateEvidenceInfoLine label="反馈消息" value={String(detail.candidate.feedback_target_message_id || '-')} />
            <CandidateEvidenceInfoLine label="记忆文件" value={detail.candidate.path} />
            <CandidateEvidenceInfoLine label="实际动作" value={candidateEvidenceActionText(detail.ref) || '-'} />
            <CandidateEvidenceInfoLine label="证据类型" value={detail.ref.evidence_family || '-'} />
          </div>
          {detail.loading && (
            <div className="mt-3 rounded border border-ops-accent/30 bg-ops-accent/10 px-3 py-2 text-xs text-ops-accent">
              正在加载来源会话执行轨迹...
            </div>
          )}
          {detail.error && (
            <div className="mt-3 rounded border border-ops-alert/35 bg-ops-alert/10 px-3 py-2 text-xs text-ops-alert">
              {detail.error}
            </div>
          )}
          {trace ? (
            <div className="mt-3">
              <ToolTraceList items={[trace]} sessionMode={sessionMode} />
            </div>
          ) : !detail.loading && !detail.error ? (
            <div className="mt-3 rounded border border-ops-surface0 bg-ops-dark/35 px-3 py-3 text-xs text-ops-subtext">
              暂未在来源会话历史中匹配到完整执行轨迹，仅保留当前候选上的证据引用。
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}

function CandidateEvidenceInfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
      <div className="text-[11px] text-ops-overlay">{label}</div>
      <div className="mt-1 truncate font-mono text-xs text-ops-subtext" title={value}>{value}</div>
    </div>
  )
}

function feedbackPolicyLabel(rating: string, policy?: string) {
  if (rating === 'up' && policy === 'pending_review') return '待确认候选'
  if (rating === 'up') return policy === 'promote' ? '成功经验已沉淀' : '好评待沉淀'
  if (policy === 'do_not_promote_answer') return '纠错审计'
  return '负反馈'
}

export function SessionMemoryActivityPanel({
  activity,
  focusMessageId,
  loading,
  onFocusMessage,
  onReload,
}: {
  activity: SessionMemoryActivity | null
  focusMessageId?: string | number | null
  loading: boolean
  onFocusMessage?: (messageId: string | number) => void
  onReload: () => void
}) {
  const focusKey = focusMessageId === undefined || focusMessageId === null ? '' : String(focusMessageId)
  const [activityDateFilter, setActivityDateFilter] = useState('all')
  const [activityMessageFilter, setActivityMessageFilter] = useState('all')
  const allFeedbackRows = activity?.feedback.slice().reverse() || []
  const allReferencedRows = activity?.referenced.slice().reverse() || []
  const activityDates = Array.from(new Set([...allFeedbackRows, ...allReferencedRows]
    .map((item) => String(item.created_at || '').slice(0, 10))
    .filter((date) => /^\d{4}-\d{2}-\d{2}$/.test(date))))
    .sort()
    .reverse()
  const activityMessages = Array.from(new Set([...allFeedbackRows, ...allReferencedRows]
    .map((item) => item.message_id)
    .filter((messageId) => messageId !== undefined && messageId !== null)
    .map((messageId) => String(messageId))))
    .sort((left, right) => Number(left) - Number(right))
  const rowMatchesActivityFilters = (item: { created_at?: string | number; message_id?: number | string | null }) => {
    const date = String(item.created_at || '').slice(0, 10)
    const messageId = item.message_id === undefined || item.message_id === null ? '' : String(item.message_id)
    return (
      (activityDateFilter === 'all' || date === activityDateFilter) &&
      (activityMessageFilter === 'all' || messageId === activityMessageFilter)
    )
  }
  const filteredFeedbackRows = allFeedbackRows.filter(rowMatchesActivityFilters)
  const filteredReferencedRows = allReferencedRows.filter(rowMatchesActivityFilters)
  const focusedFeedbackRow = focusKey
    ? filteredFeedbackRows.find((item) => String(item.message_id || '') === focusKey)
    : undefined
  const latestFeedbackRows = filteredFeedbackRows.slice(0, 6)
  const feedbackRows = focusedFeedbackRow && !latestFeedbackRows.includes(focusedFeedbackRow)
    ? [focusedFeedbackRow, ...latestFeedbackRows.slice(0, 5)]
    : latestFeedbackRows
  const referencedRows = filteredReferencedRows.slice(0, 4)
  const hasActivityFilter = activityDateFilter !== 'all' || activityMessageFilter !== 'all'
  const stats = [
    ['引用记忆', activity?.summary.referenced_count || 0],
    ['好评沉淀', activity?.summary.promoted_count || 0],
    ['差评纠错', activity?.summary.rejected_count || 0],
    ['待确认', activity?.summary.pending_conflict_count || 0],
  ]

  return (
    <section className="rounded-lg border border-ops-success/30 bg-ops-success/5 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">当前会话记忆活动</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            把左侧会话里的记忆引用、点赞沉淀和点踩纠错集中到这里，方便审计“哪条回答影响了 AI 记忆”。
          </p>
          {focusKey && (
            <div className="mt-2 inline-flex rounded-full border border-ops-accent/35 px-2 py-0.5 font-mono text-[11px] text-ops-accent">
              正在定位消息 {focusKey}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onReload}
          disabled={loading}
          className="rounded-md border border-ops-success/40 px-3 py-1.5 text-xs font-semibold text-ops-success hover:bg-ops-success/10 disabled:opacity-50"
        >
          {loading ? '加载中...' : '刷新活动'}
        </button>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-4">
        {stats.map(([label, value]) => (
          <div key={label} className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-2">
            <div className="text-[11px] text-ops-overlay">{label}</div>
            <div className="mt-1 text-lg font-semibold text-ops-text">{value}</div>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded-md border border-ops-surface0 bg-ops-dark/25 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-xs font-semibold text-ops-text">按日期 / 会话轮次筛选</div>
          {hasActivityFilter && (
            <button
              type="button"
              onClick={() => {
                setActivityDateFilter('all')
                setActivityMessageFilter('all')
              }}
              className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-[11px] text-ops-accent hover:bg-ops-accent/10"
            >
              清除筛选
            </button>
          )}
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          <label className="space-y-1 text-[11px] text-ops-overlay">
            <span>日期</span>
            <select
              value={activityDateFilter}
              onChange={(event) => setActivityDateFilter(event.target.value)}
              className="w-full rounded-md border border-ops-surface0 bg-ops-panel px-2 py-1.5 text-xs text-ops-text outline-none focus:border-ops-accent"
            >
              <option value="all">全部日期</option>
              {activityDates.map((date) => (
                <option key={date} value={date}>{date}</option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-[11px] text-ops-overlay">
            <span>会话轮次</span>
            <select
              value={activityMessageFilter}
              onChange={(event) => setActivityMessageFilter(event.target.value)}
              className="w-full rounded-md border border-ops-surface0 bg-ops-panel px-2 py-1.5 text-xs text-ops-text outline-none focus:border-ops-accent"
            >
              <option value="all">全部轮次</option>
              {activityMessages.map((messageId) => (
                <option key={messageId} value={messageId}>消息 {messageId}</option>
              ))}
            </select>
          </label>
        </div>
        <p className="mt-2 text-[11px] text-ops-overlay">
          当前范围：{filteredFeedbackRows.length} 条反馈，{filteredReferencedRows.length} 条引用。
        </p>
      </div>

      {!activity && !loading ? (
        <div className="mt-3 rounded-md border border-dashed border-ops-surface1 p-4 text-center text-xs leading-5 text-ops-subtext">
          当前没有打开会话，或该会话还没有可展示的记忆活动。
        </div>
      ) : (
        <div className="mt-3 grid gap-3 xl:grid-cols-2">
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-3">
            <div className="text-xs font-semibold text-ops-text">反馈记录</div>
            <div className="mt-2 space-y-2">
              {feedbackRows.length > 0 ? feedbackRows.map((item, index) => (
                <article
                  key={`${item.message_id || 'feedback'}-${index}`}
                  className={`rounded border px-3 py-2 ${
                    focusKey && String(item.message_id || '') === focusKey
                      ? 'border-ops-accent bg-ops-accent/10 shadow-[0_0_0_1px_rgba(45,212,191,0.22)]'
                      : 'border-ops-surface0 bg-ops-panel/55'
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <span className={`rounded-full px-2 py-0.5 ${item.rating === 'up' ? 'bg-ops-success/10 text-ops-success' : 'bg-ops-alert/10 text-ops-alert'}`}>
                      {item.rating === 'up' ? '好评' : '差评'}
                    </span>
                    {focusKey && String(item.message_id || '') === focusKey && (
                      <span className="rounded-full border border-ops-accent/45 px-2 py-0.5 text-ops-accent">
                        当前定位
                      </span>
                    )}
                    <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-ops-subtext">
                      {feedbackPolicyLabel(String(item.rating), item.memory_policy)}
                    </span>
                    <span className="font-mono text-ops-overlay">消息 {item.message_id || '-'}</span>
                    <span className="font-mono text-ops-overlay">{item.created_at || '无时间'}</span>
                    {item.message_id !== undefined && (
                      <button
                        type="button"
                        onClick={() => onFocusMessage?.(item.message_id as string | number)}
                        className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-ops-accent hover:bg-ops-accent/10"
                      >
                        回到会话
                      </button>
                    )}
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs leading-5 text-ops-subtext">{item.message_preview}</p>
                  {item.note && <div className="mt-1 text-[11px] text-ops-overlay">备注：{item.note}</div>}
                  <div className={`mt-2 rounded-md border px-2 py-1 text-[11px] leading-5 ${
                    item.rating === 'up'
                      ? 'border-ops-success/25 bg-ops-success/10 text-ops-success'
                      : 'border-ops-alert/25 bg-ops-alert/10 text-ops-alert'
                  }`}>
                    写入状态：{feedbackPolicyLabel(String(item.rating), item.memory_policy)}。
                    {item.rating === 'up' && item.memory_policy === 'pending_review'
                      ? ' 已生成候选，人工确认前不会进入模型检索上下文。'
                      : item.rating === 'up'
                        ? ' 作为当前会话成功经验保存，本会话后续轮次可引用。'
                      : ' 已标记为不佳回答，不会作为成功经验注入本会话后续轮次。'}
                  </div>
                </article>
              )) : (
                <div className="rounded border border-dashed border-ops-surface1 p-3 text-center text-xs text-ops-overlay">
                  暂无点赞或点踩记录
                </div>
              )}
            </div>
          </div>

          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 p-3">
            <div className="text-xs font-semibold text-ops-text">引用过的记忆</div>
            <div className="mt-2 space-y-2">
              {referencedRows.length > 0 ? referencedRows.map((row, index) => (
                <article
                  key={`${row.message_id || 'ref'}-${index}`}
                  className={`rounded border px-3 py-2 ${
                    focusKey && String(row.message_id || '') === focusKey
                      ? 'border-ops-accent bg-ops-accent/10 shadow-[0_0_0_1px_rgba(45,212,191,0.22)]'
                      : 'border-ops-surface0 bg-ops-panel/55'
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-ops-overlay">
                    <span>消息 {row.message_id || '-'}</span>
                    {focusKey && String(row.message_id || '') === focusKey && (
                      <span className="rounded-full border border-ops-accent/45 px-2 py-0.5 text-ops-accent">
                        当前定位
                      </span>
                    )}
                    <span>{row.created_at || '无时间'}</span>
                    <span>{row.refs.length} 条引用</span>
                    {row.message_id !== undefined && (
                      <button
                        type="button"
                        onClick={() => onFocusMessage?.(row.message_id as string | number)}
                        className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-ops-accent hover:bg-ops-accent/10"
                      >
                        回到会话
                      </button>
                    )}
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs leading-5 text-ops-subtext">{row.message_preview}</p>
                </article>
              )) : (
                <div className="rounded border border-dashed border-ops-surface1 p-3 text-center text-xs text-ops-overlay">
                  暂无长期记忆引用
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export function MemoryReviewPanel({
  items,
  reviewingPath,
  onOpen,
  onReview,
}: {
  items: MemoryReviewItem[]
  reviewingPath: string | null
  onOpen: (path: string) => void
  onReview: (item: MemoryReviewItem) => void
}) {
  return (
    <section className="rounded-lg border border-amber-400/30 bg-amber-400/5 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">需要复核的记忆</div>
          <p className="mt-1 text-xs text-ops-subtext">长期未更新的记忆会进入这里，避免旧经验静默影响当前会话后续判断。</p>
        </div>
        <span className="rounded-full border border-amber-300/35 px-2 py-0.5 text-xs text-amber-200">
          {items.length}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => (
          <article key={item.path} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
            <div className="flex items-start justify-between gap-2">
              <button
                onClick={() => onOpen(item.path)}
                className="min-w-0 truncate text-left text-xs font-semibold text-amber-200 hover:text-ops-text"
                title={item.path}
              >
                {item.path}
              </button>
              <span className="shrink-0 font-mono text-[11px] text-ops-overlay">{item.age_days} 天</span>
            </div>
            <p className="mt-1 text-xs leading-5 text-ops-subtext">{item.reason}</p>
            <p className="mt-1 text-[11px] leading-5 text-ops-overlay">{item.recommended_action}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                onClick={() => onOpen(item.path)}
                className="rounded border border-ops-surface0 px-2 py-1 text-[11px] text-ops-subtext hover:border-ops-accent/45 hover:text-ops-accent"
              >
                打开查看
              </button>
              <button
                onClick={() => onReview(item)}
                disabled={Boolean(reviewingPath)}
                className="rounded border border-amber-300/35 px-2 py-1 text-[11px] text-amber-200 hover:bg-amber-300/10 disabled:opacity-50"
              >
                {reviewingPath === item.path ? '标记中...' : '标记已复核'}
              </button>
            </div>
          </article>
        )) : (
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-4 text-center text-xs text-ops-overlay">
            暂无过期待复核记忆
          </div>
        )}
      </div>
    </section>
  )
}

export function MemoryStoresPanel({ stores }: { stores: MemoryStoreInfo[] }) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="text-sm font-semibold text-ops-text">记忆存储区</div>
      <p className="mt-1 text-xs text-ops-subtext">会话记忆只保存在当前 session；知识库/RAG 才是全局共享资料。这里展示的是 Hermes-style 的保留边界。</p>
      <div className="mt-3 space-y-2">
        {stores.map((store) => (
          <div key={store.id} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-ops-text">{store.name}</span>
              <div className="flex flex-wrap justify-end gap-1.5">
                <span className={`rounded-full px-2 py-0.5 text-[10px] ${store.access === 'read_only' ? 'bg-ops-alert/10 text-ops-alert' : 'bg-ops-success/10 text-ops-success'}`}>
                  {store.access === 'read_only' ? '只读' : '可写'}
                </span>
                <span className="rounded-full border border-ops-accent/30 px-2 py-0.5 text-[10px] text-ops-accent">
                  {store.memory_model === 'hermes_style_session_retention' ? '轨迹+压缩' : store.memory_model || '文件记忆'}
                </span>
              </div>
            </div>
            <div className="mt-1 text-xs leading-5 text-ops-subtext">{store.description}</div>
            <div className="mt-2 rounded border border-ops-surface1/70 bg-ops-dark/30 px-2 py-1 text-[11px] leading-5 text-ops-overlay">
              <div>路径：{store.path_prefix || '/'}</div>
              <div>生命周期：{store.lifecycle || '未配置'}</div>
              <div>保留逻辑：完整会话历史用于审计；压缩后的会话状态、成功经验、错误反馈才进入当前会话上下文。</div>
              <div>说明：{store.instructions || '按最小必要原则读取，写入前先验证。'}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export function MemoryQualityPanel({
  report,
  onGoGovern,
  onOpen,
  onRefresh,
}: {
  report: MemoryQualityReport | null
  onGoGovern: () => void
  onOpen: (path: string) => void
  onRefresh: () => void
}) {
  const summary = report?.summary
  const stores = report?.stores || []
  const candidates = report?.compression_candidates || []
  const healthScore = summary?.health_score ?? 0
  const healthTone = healthScore >= 80 ? 'text-ops-success' : healthScore >= 60 ? 'text-amber-200' : 'text-ops-alert'
  const qualityCards = [
    ['健康分', `${healthScore}`, '按冲突、过期、重复和碎片化综合估算'],
    ['记忆条目', `${summary?.entry_count ?? 0}`, `${summary?.memory_count ?? 0} 个文件 / ${summary?.store_count ?? 0} 个库`],
    ['待处理', `${(summary?.pending_conflict_count ?? 0) + (summary?.stale_review_count ?? 0)}`, '冲突与过期内容建议复核'],
    ['待压缩', `${summary?.compression_candidate_count ?? 0}`, '先生成摘要建议，不自动覆盖已保存记忆'],
  ]

  return (
    <section className="rounded-xl border border-ops-surface0 bg-gradient-to-br from-ops-panel/85 via-ops-panel/55 to-ops-dark/70 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.22)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ops-text">记忆质量仪表盘</div>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-ops-subtext">
            把 AI 记忆保存成可查看、可整理、可回退的文件；这里先给出管理建议，避免旧经验影响当前会话后续判断。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={onRefresh} className="rounded-md border border-ops-surface1 px-3 py-1.5 text-xs text-ops-subtext hover:border-ops-accent hover:text-ops-text">
            刷新质量
          </button>
          <button onClick={onGoGovern} className="rounded-md border border-ops-accent/50 bg-ops-accent/10 px-3 py-1.5 text-xs font-semibold text-ops-accent hover:bg-ops-accent hover:text-ops-dark">
            去治理
          </button>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        {qualityCards.map(([label, value, hint], index) => (
          <div key={label} className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
            <div className="text-[11px] uppercase tracking-[0.22em] text-ops-overlay">{label}</div>
            <div className={`mt-2 text-2xl font-black ${index === 0 ? healthTone : 'text-ops-text'}`}>{value}</div>
            <div className="mt-1 text-[11px] leading-4 text-ops-subtext">{hint}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-[0.95fr_1.2fr]">
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ops-text">记忆库分布</span>
            <span className="text-[11px] text-ops-overlay">{report?.policy?.rule || '简单模式，先保存原文和摘要。'}</span>
          </div>
          <div className="mt-3 space-y-2">
            {stores.length > 0 ? stores.map((store) => (
              <div key={store.store_id} className="rounded-md border border-ops-surface1/70 bg-ops-panel/35 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-ops-text">{store.store_name}</span>
                  <span className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-subtext">{store.store_id === 'global' ? '只读' : '可写'}</span>
                </div>
                <div className="mt-2 grid grid-cols-4 gap-2 text-[11px] text-ops-subtext">
                  <span>{store.memories} 文件</span>
                  <span>{store.entries} 条</span>
                  <span>{formatMemorySize(store.size)}</span>
                  <span>{candidates.filter((candidate) => candidate.store_id === store.store_id).length} 摘要建议</span>
                </div>
              </div>
            )) : (
              <div className="rounded-md border border-dashed border-ops-surface1 p-4 text-xs text-ops-subtext">暂无质量数据，刷新后会显示各个记忆库的分布。</div>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ops-text">待压缩记忆</span>
            <span className="text-[11px] text-ops-overlay">不会自动覆盖，先保留原文和摘要</span>
          </div>
          <div className="mt-3 space-y-2">
            {candidates.length > 0 ? candidates.map((candidate) => (
              <button
                key={candidate.path}
                onClick={() => onOpen(candidate.path)}
                className="w-full rounded-md border border-amber-300/25 bg-amber-300/5 px-3 py-2 text-left transition-colors hover:border-amber-300/55 hover:bg-amber-300/10"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-ops-text">{candidate.path}</span>
                  <span className="rounded-full bg-amber-300/10 px-2 py-0.5 text-[10px] text-amber-200">评分 {candidate.score}</span>
                </div>
                <div className="mt-1 text-[11px] text-ops-subtext">
                  {candidate.store_name || candidate.store_id || '未分组'} / {candidate.entries} 条 / {formatMemorySize(candidate.size)}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {candidate.reason.split('；').filter(Boolean).map((reason) => (
                    <span key={reason} className="rounded-full border border-ops-surface1 px-2 py-0.5 text-[10px] text-ops-overlay">{reason}</span>
                  ))}
                </div>
              </button>
            )) : (
              <div className="rounded-md border border-dashed border-ops-surface1 p-4 text-xs leading-5 text-ops-subtext">
                当前没有明显需要压缩的记忆。后续如果某个会话记忆过多，会先进入这里排队，再由你确认是否整理。
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

export function MemoryVersionsPanel({
  versions,
  redactingVersionId,
  onRedact,
  onRestore,
}: {
  versions: MemoryVersion[]
  redactingVersionId: string | null
  onRedact: (version: MemoryVersion) => void
  onRestore: (version: MemoryVersion) => void
}) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="text-sm font-semibold text-ops-text">版本审计</div>
      <p className="mt-1 text-xs text-ops-subtext">记录 AI 记忆创建、修改和删除轨迹，方便追溯来源。</p>
      <div className="mt-3 space-y-2">
        {versions.length > 0 ? versions.slice(0, 8).map((version, index) => (
          <div key={`${version.timestamp}-${version.path}-${index}`} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-ops-text">{version.operation}</span>
              <span className="text-[11px] text-ops-overlay">{version.timestamp}{version.redacted ? ' · 已脱敏' : ''}</span>
            </div>
            <div className="mt-1 flex items-center gap-2">
              <div className="min-w-0 flex-1 truncate text-xs text-ops-subtext" title={version.path}>{version.path}</div>
              <button
                onClick={() => onRedact(version)}
                disabled={!version.version_id || Boolean(redactingVersionId) || version.redacted}
                className="rounded border border-ops-alert/40 px-2 py-0.5 text-[11px] text-ops-alert hover:bg-ops-alert/10 disabled:opacity-40"
                title="脱敏历史版本中的内容，保留版本审计元数据"
              >
                {redactingVersionId === version.version_id ? '脱敏中...' : '脱敏'}
              </button>
              <button
                onClick={() => onRestore(version)}
                disabled={!version.version_id || version.redacted}
                className="rounded border border-ops-surface0 px-2 py-0.5 text-[11px] text-ops-overlay hover:border-ops-accent/45 hover:text-ops-accent disabled:opacity-40"
              >
                恢复
              </button>
            </div>
          </div>
        )) : (
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-4 text-center text-xs text-ops-overlay">
            暂无版本记录
          </div>
        )}
      </div>
    </section>
  )
}

export function MemoryDeleteDialog({
  deleting,
  target,
  onCancel,
  onConfirm,
}: {
  deleting: boolean
  target: MemoryItem
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" onClick={() => !deleting && onCancel()}>
      <section className="w-full max-w-md rounded-lg border border-ops-surface1 bg-ops-panel shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="border-b border-ops-surface0 px-5 py-4">
          <div className="text-xs font-semibold text-ops-alert">删除 AI 记忆</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">确认删除</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">
            删除后该记忆不会再参与当前会话后续检索，同时会写入删除版本审计。
          </p>
        </div>
        <div className="p-5">
          <div className="break-all rounded-lg border border-ops-surface0 bg-ops-dark/45 px-3 py-2 text-sm font-semibold text-ops-text">
            {target.path}
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-4">
          <button onClick={onCancel} disabled={deleting} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text disabled:opacity-50">
            取消
          </button>
          <button onClick={onConfirm} disabled={deleting} className="rounded-lg bg-ops-alert px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {deleting ? '删除中...' : '确认删除'}
          </button>
        </div>
      </section>
    </div>
  )
}
