import { useEffect, useMemo, useState } from 'react'
import {
  getSessionRetentionConfig,
  runSessionRetentionNow,
  updateSessionRetentionConfig,
  type SessionRetentionConfig,
} from '@/api/config'
import { useStore } from '@/store'

const DEFAULT_DRAFT: SessionRetentionConfig = {
  enabled: true,
  raw_result_days: 30,
  compressed_history_days: 180,
  audit_metadata_days: 365,
  max_result_chars: 2000,
  preview_chars: 1200,
}

export default function SessionRetentionConfigModal() {
  const closeModal = useStore((state) => state.closeModal)
  const addToast = useStore((state) => state.addToast)
  const [draft, setDraft] = useState<SessionRetentionConfig>(DEFAULT_DRAFT)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getSessionRetentionConfig(true)
      .then((response) => {
        if (!cancelled) setDraft({ ...DEFAULT_DRAFT, ...response.data.config })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载会话保留策略失败')
          addToast('加载会话保留策略失败', 'error')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [addToast])

  const validationError = useMemo(() => validateDraft(draft), [draft])

  const updateDraft = (patch: Partial<SessionRetentionConfig>) => {
    setDraft((current) => ({ ...current, ...patch }))
  }

  const save = async () => {
    const invalid = validateDraft(draft)
    if (invalid) {
      addToast(invalid, 'error')
      return
    }
    setSaving(true)
    try {
      const response = await updateSessionRetentionConfig(draft)
      setDraft({ ...DEFAULT_DRAFT, ...response.data.config })
      addToast('会话保留策略已保存', 'success')
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '保存会话保留策略失败', 'error')
    }
    setSaving(false)
  }

  const runNow = async () => {
    setRunning(true)
    try {
      const response = await runSessionRetentionNow()
      const result = response.data.result
      setDraft((current) => ({
        ...current,
        preview: result,
        status: {
          ...current.status,
          last_run: result,
          next_run_at: nextRunAt(result.completed_at, current.status?.interval_seconds ?? current.interval_seconds),
          interval_seconds: current.status?.interval_seconds ?? current.interval_seconds,
        },
      }))
      addToast('会话保留策略已执行', 'success')
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '执行会话保留策略失败', 'error')
    }
    setRunning(false)
  }

  return (
    <div className="ops-modal-backdrop" onClick={closeModal}>
      <div
        className="ops-modal-surface flex h-[min(720px,94vh)] w-full max-w-4xl flex-col"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="ops-modal-header">
          <div>
            <h2 className="ops-modal-title">会话保留策略</h2>
            <p className="ops-modal-description">统一控制聊天历史、工具结果和执行链路的保留周期。</p>
          </div>
          <button onClick={closeModal} className="ops-icon-button" title="关闭">&times;</button>
        </div>

        <div className="ops-modal-body p-6">
          {error && (
            <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
              {error}
            </div>
          )}
          {loading ? (
            <div className="flex h-full items-center justify-center text-sm text-ops-subtext">
              正在读取会话保留策略...
            </div>
          ) : (
            <div className="space-y-4">
              <div className="ops-data-panel p-4">
                <label className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-sm font-semibold text-ops-text">启用自动保留策略</div>
                    <div className="mt-1 text-xs leading-5 text-ops-subtext">
                      后台默认每 24 小时执行一轮；超过周期的数据会先摘要化，再按压缩状态清理。
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={draft.enabled}
                    onChange={(event) => updateDraft({ enabled: event.target.checked })}
                    className="h-5 w-5 accent-ops-accent"
                  />
                </label>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <RetentionNumberField
                  label="工具结果原文"
                  suffix="天后摘要化"
                  value={draft.raw_result_days}
                  onChange={(value) => updateDraft({ raw_result_days: value })}
                />
                <RetentionNumberField
                  label="压缩历史原文"
                  suffix="天后删除"
                  value={draft.compressed_history_days}
                  onChange={(value) => updateDraft({ compressed_history_days: value })}
                />
                <RetentionNumberField
                  label="审计元数据"
                  suffix="天后清理"
                  value={draft.audit_metadata_days}
                  onChange={(value) => updateDraft({ audit_metadata_days: value })}
                />
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <RetentionNumberField
                  label="结果最大保留长度"
                  suffix="字符"
                  value={draft.max_result_chars}
                  min={200}
                  max={100000}
                  onChange={(value) => updateDraft({ max_result_chars: value })}
                />
                <RetentionNumberField
                  label="摘要预览长度"
                  suffix="字符"
                  value={draft.preview_chars}
                  min={200}
                  max={20000}
                  onChange={(value) => updateDraft({ preview_chars: value })}
                />
              </div>

              {validationError && (
                <div className="rounded-lg border border-amber-400/35 bg-amber-400/10 px-4 py-3 text-xs leading-5 text-amber-200">
                  {validationError}
                </div>
              )}

              <RetentionStatus config={draft} />
              <RetentionPreview config={draft} />
            </div>
          )}
        </div>

        <div className="ops-modal-footer justify-between">
          <div className="text-[11px] text-ops-overlay">
            保存后写入环境配置，重启后仍保留；命令和 SQL 不会因为结果摘要化而删除。
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => void runNow()}
              disabled={running || loading || Boolean(validationError)}
              className="ops-muted-action px-4 py-2 text-sm disabled:opacity-50"
            >
              {running ? '执行中...' : '立即执行一次'}
            </button>
            <button onClick={closeModal} className="ops-control rounded-lg px-4 py-2 text-sm font-semibold">
              取消
            </button>
            <button
              onClick={() => void save()}
              disabled={saving || loading || Boolean(validationError)}
              className="ops-primary-action px-4 py-2 text-sm disabled:opacity-50"
            >
              {saving ? '保存中...' : '保存策略'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function RetentionStatus({ config }: { config: SessionRetentionConfig }) {
  const status = config.status
  const lastRun = status?.last_run
  return (
    <div className="ops-data-panel p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold text-ops-text">后台执行状态</div>
        <span className="rounded-full border border-ops-surface0 bg-ops-dark/35 px-2 py-1 text-[10px] text-ops-overlay">
          {formatInterval(status?.interval_seconds ?? config.interval_seconds)}
        </span>
      </div>
      <div className="grid gap-2 text-xs text-ops-subtext md:grid-cols-4">
        <StatusCell label="最近执行" value={formatDateTime(lastRun?.completed_at)} />
        <StatusCell label="下一次执行" value={formatDateTime(status?.next_run_at)} />
        <StatusCell label="耗时" value={formatDuration(lastRun?.duration_ms)} />
        <StatusCell label="状态" value={lastRun?.status === 'completed' ? '完成' : '暂无记录'} />
      </div>
      {lastRun && (
        <div className="mt-3 grid gap-2 text-xs text-ops-subtext sm:grid-cols-4">
          <PreviewStat label="扫描" value={lastRun.rows_scanned} />
          <PreviewStat label="摘要化" value={lastRun.rows_compacted} />
          <PreviewStat label="删除历史" value={lastRun.rows_deleted} warn={Boolean(lastRun.rows_deleted)} />
          <PreviewStat label="清理审计" value={lastRun.audit_rows_deleted || 0} />
        </div>
      )}
      {status?.error && <div className="mt-3 text-xs text-ops-alert">{status.error}</div>}
    </div>
  )
}

function StatusCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
      <div className="text-[10px] text-ops-overlay">{label}</div>
      <div className="mt-1 min-h-5 break-words text-sm font-medium text-ops-text">{value}</div>
    </div>
  )
}

function RetentionNumberField({
  label,
  max = 3650,
  min = 1,
  onChange,
  suffix,
  value,
}: {
  label: string
  max?: number
  min?: number
  onChange: (value: number) => void
  suffix: string
  value: number
}) {
  return (
    <label className="ops-data-panel block p-4">
      <span className="text-xs text-ops-subtext">{label}</span>
      <div className="mt-2 flex items-center gap-2">
        <input
          type="number"
          min={min}
          max={max}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          className="ops-control min-w-0 flex-1 px-3 py-2 text-sm"
        />
        <span className="whitespace-nowrap text-[11px] text-ops-overlay">{suffix}</span>
      </div>
    </label>
  )
}

function RetentionPreview({ config }: { config: SessionRetentionConfig }) {
  const preview = config.preview
  if (!preview) {
    return (
      <div className="ops-data-panel p-4 text-xs text-ops-subtext">
        暂无当前库影响预览。
      </div>
    )
  }
  return (
    <div className="ops-data-panel p-4">
      <div className="mb-3 text-sm font-semibold text-ops-text">当前库影响预览</div>
      <div className="grid gap-2 text-xs text-ops-subtext sm:grid-cols-4">
        <PreviewStat label="扫描" value={preview.rows_scanned} />
        <PreviewStat label="摘要化" value={preview.rows_compacted} />
        <PreviewStat label="删除历史" value={preview.rows_deleted} warn={Boolean(preview.rows_deleted)} />
        <PreviewStat label="清理审计" value={preview.audit_rows_deleted || 0} />
      </div>
      {preview.error && <div className="mt-3 text-xs text-ops-alert">{preview.error}</div>}
    </div>
  )
}

function PreviewStat({ label, value, warn = false }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 px-3 py-2">
      <div className="text-[10px] text-ops-overlay">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${warn ? 'text-amber-300' : 'text-ops-accent'}`}>{value}</div>
    </div>
  )
}

function formatDateTime(value?: string | null) {
  if (!value) return '暂无'
  return value.replace('T', ' ').slice(0, 19)
}

function formatDuration(value?: number) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '暂无'
  if (value < 1000) return `${value} ms`
  return `${(value / 1000).toFixed(1)} s`
}

function formatInterval(value?: number | null) {
  if (!value) return '周期未读取'
  if (value % 86400 === 0) return `${value / 86400} 天一轮`
  if (value % 3600 === 0) return `${value / 3600} 小时一轮`
  if (value % 60 === 0) return `${value / 60} 分钟一轮`
  return `${value} 秒一轮`
}

function nextRunAt(completedAt?: string, intervalSeconds?: number | null) {
  if (!completedAt || !intervalSeconds) return null
  const completed = new Date(completedAt.replace(' ', 'T'))
  if (Number.isNaN(completed.getTime())) return null
  return new Date(completed.getTime() + intervalSeconds * 1000).toISOString().slice(0, 19).replace('T', ' ')
}

function validateDraft(config: SessionRetentionConfig) {
  if (config.raw_result_days > config.compressed_history_days) {
    return '工具结果摘要化周期不能大于压缩历史删除周期。'
  }
  if (config.compressed_history_days > config.audit_metadata_days) {
    return '压缩历史删除周期不能大于审计元数据保留周期。'
  }
  if (config.preview_chars > config.max_result_chars) {
    return '摘要预览长度不能大于结果最大保留长度。'
  }
  return ''
}
