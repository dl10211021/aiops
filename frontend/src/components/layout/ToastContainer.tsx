import { useStore } from '@/store'

export default function ToastContainer() {
  const toasts = useStore((s) => s.toasts)
  const removeToast = useStore((s) => s.removeToast)

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          onClick={() => removeToast(t.id)}
          className={`cursor-pointer rounded-xl border px-4 py-3 text-sm shadow-[0_18px_45px_rgba(0,0,0,0.32)] backdrop-blur-xl animate-in slide-in-from-right
            ${t.type === 'success' ? 'border-ops-success/35 bg-ops-success/16 text-ops-success' : ''}
            ${t.type === 'error' ? 'border-ops-alert/35 bg-ops-alert/16 text-ops-alert' : ''}
            ${t.type === 'info' ? 'border-ops-accent/35 bg-ops-panel/92 text-ops-accent' : ''}`}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
