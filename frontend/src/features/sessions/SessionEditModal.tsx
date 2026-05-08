import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { Session } from '@/types'
import { protocolLabel } from '@/utils/assetDisplay'
import { normalizeSessionGroupName, sessionPrimaryGroup, uniqueSessionGroups } from './sessionGroups'

const CUSTOM_GROUP_OPTION = '__custom_session_group__'

export interface SessionEditValues {
  groupName: string
  remark: string
  tags: string[]
}

interface SessionEditModalProps {
  busy: boolean
  groupNames: string[]
  session: Session
  onClose: () => void
  onSave: (values: SessionEditValues) => void
}

export default function SessionEditModal({
  busy,
  groupNames,
  session,
  onClose,
  onSave,
}: SessionEditModalProps) {
  const currentGroup = sessionPrimaryGroup(session)
  const [remark, setRemark] = useState(session.remark || '')
  const [groupName, setGroupName] = useState(currentGroup)
  const [customGroupName, setCustomGroupName] = useState('')
  const [tagsText, setTagsText] = useState(sessionUserTags(session).join(', '))
  const [formError, setFormError] = useState('')

  useEffect(() => {
    setRemark(session.remark || '')
    setGroupName(sessionPrimaryGroup(session))
    setCustomGroupName('')
    setTagsText(sessionUserTags(session).join(', '))
    setFormError('')
  }, [session])

  const selectableGroups = useMemo(
    () => uniqueSessionGroups([currentGroup, ...groupNames]),
    [currentGroup, groupNames],
  )

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const nextGroup = normalizeSessionGroupName(
      groupName === CUSTOM_GROUP_OPTION ? customGroupName : groupName,
    )
    if (!nextGroup) {
      setFormError('会话组不能为空')
      return
    }
    setFormError('')
    onSave({
      groupName: nextGroup,
      remark: remark.trim(),
      tags: parseTags(tagsText).filter((tag) => tag !== nextGroup),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 px-4" onClick={onClose}>
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-[520px] rounded-lg border border-ops-surface1 bg-ops-panel p-4 shadow-[var(--ops-panel-shadow)]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-ops-text">编辑单个会话</h2>
            <div className="mt-1 truncate text-[11px] text-ops-overlay">
              修改会话名称、所属分组和标签，不会修改资产连接凭据。
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-xs text-ops-overlay hover:bg-ops-surface0 hover:text-ops-text"
            title="关闭"
          >
            关闭
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 rounded-lg border border-ops-surface0 bg-ops-dark/35 p-3 text-[11px]">
          <ReadOnlyField label="资产" value={session.host || '-'} />
          <ReadOnlyField label="账号" value={session.user || '-'} />
          <ReadOnlyField label="协议" value={protocolLabel(session.protocol || session.asset_type)} />
          <ReadOnlyField label="模式" value={session.isReadWriteMode ? '读写' : '只读'} />
        </div>

        <div className="mt-3 space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-ops-subtext">会话名称</span>
            <input
              value={remark}
              onChange={(event) => setRemark(event.target.value)}
              maxLength={200}
              placeholder={`默认使用主机名：${session.host}`}
              className="w-full rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-ops-subtext">所属分组</span>
            <select
              value={groupName}
              onChange={(event) => {
                setGroupName(event.target.value)
                setFormError('')
              }}
              className="w-full rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none transition-colors focus:border-ops-accent"
            >
              {selectableGroups.map((group) => (
                <option key={group} value={group}>{group}</option>
              ))}
              <option value={CUSTOM_GROUP_OPTION}>输入新的会话组...</option>
            </select>
          </label>

          {groupName === CUSTOM_GROUP_OPTION && (
            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-ops-subtext">新会话组名称</span>
              <input
                autoFocus
                value={customGroupName}
                onChange={(event) => {
                  setCustomGroupName(event.target.value)
                  setFormError('')
                }}
                maxLength={80}
                placeholder="例如：生产数据库、网络设备"
                className="w-full rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent"
              />
            </label>
          )}

          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-ops-subtext">普通标签</span>
            <input
              value={tagsText}
              onChange={(event) => setTagsText(event.target.value)}
              placeholder="例如：P0, 数据库, 生产；这里不需要再填写分组名"
              className="w-full rounded-md border border-ops-surface1 bg-ops-dark/45 px-3 py-2 text-sm text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent"
            />
          </label>
          <div className="rounded-md border border-ops-surface0 bg-ops-dark/30 px-3 py-2 text-[11px] leading-5 text-ops-overlay">
            保存后会把「所属分组」写到会话分组字段，普通标签只作为辅助筛选；两者互不混用。
          </div>
          {formError && (
            <div className="rounded-md border border-ops-alert/35 bg-ops-alert/10 px-3 py-2 text-xs text-ops-alert">
              {formError}
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded-md px-3 py-2 text-xs font-semibold text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text disabled:opacity-50"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md border border-ops-accent/50 bg-ops-accent/12 px-3 py-2 text-xs font-bold text-ops-accent hover:bg-ops-accent/18 disabled:opacity-50"
          >
            {busy ? '保存中...' : '保存'}
          </button>
        </div>
      </form>
    </div>
  )
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-ops-overlay">{label}</div>
      <div className="mt-0.5 truncate text-ops-subtext">{value}</div>
    </div>
  )
}

function parseTags(value: string): string[] {
  const tags: string[] = []
  for (const item of value.split(/[,，\n]/)) {
    const tag = item.trim().replace(/\s+/g, ' ').slice(0, 80)
    if (tag && !tags.includes(tag)) tags.push(tag)
  }
  return tags
}

function sessionUserTags(session: Session): string[] {
  const primaryGroup = sessionPrimaryGroup(session)
  return (session.tags || [])
    .map((tag) => normalizeSessionGroupName(tag))
    .filter((tag, index) => tag && (index > 0 || tag !== primaryGroup))
}
