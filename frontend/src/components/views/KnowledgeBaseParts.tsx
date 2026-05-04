import type { ChangeEvent } from 'react'
import type { KnowledgeFile, MemoryDetail, MemoryItem, MemoryPendingConflict, MemoryReviewItem, MemoryVersion } from '@/types'
import { ACCEPTED_KNOWLEDGE_TYPES, knowledgeFileKind } from './knowledgeBaseModel'

export type KnowledgeTab = 'documents' | 'memory'

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
    ['documents', '知识文档', `${documentCount} 个文件`],
    ['memory', 'AI 记忆', `${memoryCount} 条记忆文件`],
  ]
  return (
    <div className="mb-4 flex flex-wrap gap-2 rounded-lg border border-ops-surface0 bg-ops-panel/55 p-1">
      {tabs.map(([id, label, desc]) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`rounded-md px-4 py-2 text-left transition-colors ${
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
    <label className="bg-ops-accent text-ops-dark text-sm px-3 py-1.5 rounded-lg font-medium hover:bg-ops-accent/80 transition-colors cursor-pointer">
      {uploading ? '上传中...' : '上传文档'}
      <UploadInput disabled={uploading} onUpload={onUpload} />
    </label>
  )
}

export function KnowledgeFileCard({
  file,
  onDelete,
}: {
  file: KnowledgeFile
  onDelete: (file: KnowledgeFile) => void
}) {
  const kind = knowledgeFileKind(file.filename)
  return (
    <div className="bg-ops-panel border border-ops-surface0 rounded-lg px-4 py-3 flex items-center gap-3 hover:border-ops-accent/40 transition-colors">
      <span className={`grid h-9 w-12 shrink-0 place-items-center rounded border bg-ops-dark text-[11px] font-semibold ${kind.className}`}>{kind.label}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-ops-text truncate">{file.filename}</div>
        <div className="text-xs text-ops-overlay">
          {file.chunks !== undefined && `${file.chunks} 个向量块`}
          {file.size !== undefined && ` · ${(file.size / 1024).toFixed(1)} KB`}
        </div>
      </div>
      <button
        onClick={() => onDelete(file)}
        className="rounded-lg px-2 py-1 text-xs text-ops-overlay transition-colors hover:bg-ops-alert/10 hover:text-ops-alert"
        title="删除"
      >
        删除
      </button>
    </div>
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
          上传巡检 SOP、故障处理记录、系统架构说明、变更规范或日志样例后，AI 会在会话和巡检中引用这些资料。
        </p>
        <label className="mt-5 inline-flex cursor-pointer rounded-lg bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark transition-colors hover:bg-ops-accent/85">
          上传第一份文档
          <UploadInput disabled={uploading} onUpload={onUpload} />
        </label>
      </section>
      <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
        {[
          ['支持格式', 'PDF、Markdown、TXT、Word、日志文件'],
          ['推荐内容', '排障手册、变更流程、资产说明、巡检标准'],
          ['使用位置', 'AI 会话、自动巡检、告警分析、技能上下文'],
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
  return (
    <article className={`rounded-lg border bg-ops-panel px-4 py-3 transition-colors ${selected ? 'border-ops-accent/70' : 'border-ops-surface0 hover:border-ops-accent/35'}`}>
      <div className="flex items-start gap-3">
        <span className="grid h-9 w-12 shrink-0 place-items-center rounded border border-ops-accent/35 bg-ops-dark text-[11px] font-semibold text-ops-accent">
          {scopeLabel}
        </span>
        <div className="min-w-0 flex-1">
          <button
            onClick={() => onOpen(item)}
            className="block max-w-full truncate text-left text-sm font-semibold text-ops-text hover:text-ops-accent"
            title={item.path}
          >
            {item.path}
          </button>
          <div className="mt-1 text-xs text-ops-overlay">
            {item.entries} 条 · {(item.size / 1024).toFixed(1)} KB · {item.updated_at}
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
        <div className="mt-1 text-xs text-ops-overlay">
          {memory.store_name || memory.scope_id} · {memory.access === 'read_only' ? '只读' : '可写'} · {(memory.size / 1024).toFixed(1)} KB · {memory.updated_at}
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
          <p className="mt-1 text-xs text-ops-subtext">长期未更新的记忆会进入这里，避免旧经验静默影响新会话。</p>
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

export function MemoryStoresPanel({ stores }: { stores: Array<{ id: string; name: string; description: string; access: string }> }) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-panel/60 p-4">
      <div className="text-sm font-semibold text-ops-text">Memory Stores</div>
      <p className="mt-1 text-xs text-ops-subtext">按 Claude 风格划分的记忆库权限和生命周期。</p>
      <div className="mt-3 space-y-2">
        {stores.map((store) => (
          <div key={store.id} className="rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-ops-text">{store.name}</span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] ${store.access === 'read_only' ? 'bg-ops-alert/10 text-ops-alert' : 'bg-ops-success/10 text-ops-success'}`}>
                {store.access === 'read_only' ? '只读' : '可写'}
              </span>
            </div>
            <div className="mt-1 text-xs leading-5 text-ops-subtext">{store.description}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

export function MemoryVersionsPanel({
  versions,
  onRestore,
}: {
  versions: MemoryVersion[]
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
              <span className="text-[11px] text-ops-overlay">{version.timestamp}</span>
            </div>
            <div className="mt-1 flex items-center gap-2">
              <div className="min-w-0 flex-1 truncate text-xs text-ops-subtext" title={version.path}>{version.path}</div>
              <button
                onClick={() => onRestore(version)}
                disabled={!version.version_id}
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
            删除后该记忆不会再参与后续会话检索，同时会写入删除版本审计。
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
