import type { ChatAttachmentPreview } from './chatTypes'
import { formatBytes } from './format'

interface AttachmentPreviewStripProps {
  attachments: ChatAttachmentPreview[]
  onRemove: (id: string) => void
}

export default function AttachmentPreviewStrip({ attachments, onRemove }: AttachmentPreviewStripProps) {
  return (
    <div className="mb-2 grid gap-2 md:grid-cols-2">
      {attachments.map((file) => (
        <div key={file.id} className="rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 gap-3">
              {file.previewUrl && (
                <img
                  src={file.previewUrl}
                  alt={file.filename}
                  className="h-12 w-12 shrink-0 rounded-md border border-ops-surface1 object-cover"
                />
              )}
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-ops-text">{file.filename}</div>
                <div className="mt-1 text-[11px] text-ops-overlay">
                  {file.ext || file.kind || '文件'} · {formatBytes(file.size)}
                  {file.rows !== undefined ? ` · ${file.rows} 行` : ''}
                  {file.pages !== undefined ? ` · ${file.pages} 页` : ''}
                  {file.truncated ? ' · 已截断' : ''}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onRemove(file.id)}
              className="shrink-0 rounded-md border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext hover:text-ops-text"
            >
              移除
            </button>
          </div>
          <pre className="mt-2 max-h-24 overflow-y-auto whitespace-pre-wrap break-all rounded-md border border-ops-surface0 bg-ops-panel/45 px-2 py-2 text-[11px] leading-4 text-ops-subtext">
            {(file.text || '[没有解析出可读文本]').slice(0, 1200)}
          </pre>
        </div>
      ))}
    </div>
  )
}
