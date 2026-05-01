import type { ReactNode } from 'react'

export default function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-5 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-[11px] font-semibold text-ops-accent">{eyebrow}</p>
        )}
        <h1 className="mt-1 text-2xl font-black text-ops-text">{title}</h1>
        {description && (
          <p className="mt-1 max-w-4xl text-sm leading-6 text-ops-subtext">{description}</p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap gap-2">
          {actions}
        </div>
      )}
    </div>
  )
}
