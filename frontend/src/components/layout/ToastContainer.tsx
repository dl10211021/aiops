import { useStore } from '@/store'

export default function ToastContainer() {
  const toasts = useStore((s) => s.toasts)
  const removeToast = useStore((s) => s.removeToast)

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          onClick={() => removeToast(t.id)}
          className={`px-4 py-2.5 rounded-lg shadow-lg text-sm cursor-pointer animate-in slide-in-from-right
            ${t.type === 'success' ? 'bg-ops-success/90 text-ops-dark' : ''}
            ${t.type === 'error' ? 'bg-ops-alert/90 text-white' : ''}
            ${t.type === 'info' ? 'bg-ops-accent/90 text-ops-dark' : ''}`}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
