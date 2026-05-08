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
    <div className="ops-page-header flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <p className="ops-page-eyebrow">{eyebrow}</p>
        )}
        <h1 className="ops-page-title">{title}</h1>
        {description && (
          <p className="ops-page-description">{description}</p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  )
}
