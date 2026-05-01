import { useState } from 'react'
import type { UserInteractionRequest } from '@/types'

interface UserInteractionCardProps {
  interaction: UserInteractionRequest
  onSubmit: (requestId: string, value: string, label?: string) => void
}

export default function UserInteractionCard({ interaction, onSubmit }: UserInteractionCardProps) {
  const [value, setValue] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const isPassword = interaction.inputType === 'password'
  const isChoice = interaction.inputType === 'choice'
  const options = interaction.options || []
  const isTimeout = interaction.status === 'timeout'

  const submitValue = async (nextValue: string, label = '') => {
    if (interaction.resolved || submitting) return
    if (interaction.required !== false && !nextValue.trim()) return
    setSubmitting(true)
    try {
      await Promise.resolve(onSubmit(interaction.requestId, nextValue, label))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="overflow-hidden rounded-lg border border-ops-accent/35 bg-ops-accent/5">
      <div className="border-b border-ops-accent/20 px-4 py-3">
        <div className="text-xs font-semibold text-ops-accent">需要你补充信息</div>
        <div className="mt-1 text-[15px] leading-relaxed text-ops-text">{interaction.prompt}</div>
      </div>

      {interaction.resolved ? (
        <div className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
          <span className={isTimeout ? 'text-ops-alert' : 'text-ops-success'}>
            {isTimeout ? '已超时，AI 已按超时结果继续。' : '已提交，AI 将继续处理。'}
          </span>
          {(interaction.label || interaction.value) && (
            <span className="max-w-[55%] truncate rounded-full border border-ops-surface1 bg-ops-panel px-3 py-1 text-xs text-ops-subtext">
              {interaction.label || interaction.value}
            </span>
          )}
        </div>
      ) : isChoice ? (
        <div className="grid gap-2 p-3 md:grid-cols-2">
          {options.map((option, index) => (
            <button
              key={`${option.value}-${index}`}
              type="button"
              disabled={submitting}
              onClick={() => submitValue(option.value, option.label)}
              className="rounded-lg border border-ops-surface1 bg-ops-panel/80 px-3 py-2 text-left transition-colors hover:border-ops-accent/70 hover:bg-ops-surface0 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <div className="text-sm font-medium text-ops-text">{option.label}</div>
              {option.description && (
                <div className="mt-1 text-xs leading-relaxed text-ops-subtext">{option.description}</div>
              )}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2 p-3 sm:flex-row">
          <input
            value={value}
            type={isPassword ? 'password' : 'text'}
            autoComplete={isPassword ? 'new-password' : 'off'}
            placeholder={interaction.placeholder || (isPassword ? '输入后仅用于本次会话' : '请输入补充信息')}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                submitValue(value)
              }
            }}
            className="min-w-0 flex-1 rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent"
          />
          <button
            type="button"
            disabled={submitting || (interaction.required !== false && !value.trim())}
            onClick={() => submitValue(value)}
            className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-semibold text-ops-dark transition-colors hover:bg-ops-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            提交
          </button>
        </div>
      )}
    </section>
  )
}
