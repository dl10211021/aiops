import { useStore } from '@/store'
import { clearSessionHistory, exportSessionHistory } from '@/api/client'

export default function SessionActionsModal() {
  const closeModal = useStore((s) => s.closeModal)
  const currentSessionId = useStore((s) => s.currentSessionId)
  const sessions = useStore((s) => s.sessions)
  const clearMessages = useStore((s) => s.clearMessages)
  const addToast = useStore((s) => s.addToast)

  const session = currentSessionId ? sessions[currentSessionId] : null

  const handleClearHistory = async () => {
    if (!currentSessionId) return
    if (!confirm('确定要清空此会话的所有聊天记录？')) return
    try {
      await clearSessionHistory(currentSessionId)
      clearMessages(currentSessionId)
      addToast('聊天记录已清空', 'success')
      closeModal()
    } catch {
      addToast('清空失败', 'error')
    }
  }

  const handleExport = async () => {
    if (!currentSessionId) return
    try {
      const res = await exportSessionHistory(currentSessionId)
      if (res.data.markdown) {
        const blob = new Blob([res.data.markdown], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `chat_${session?.remark || session?.host || currentSessionId}.md`
        a.click()
        URL.revokeObjectURL(url)
        addToast('导出成功', 'success')
      } else {
        addToast('无可导出内容', 'info')
      }
    } catch {
      addToast('导出失败', 'error')
    }
    closeModal()
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-5 w-[320px]" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-sm font-bold text-ops-text mb-3">会话操作</h2>
        <div className="space-y-1.5">
          <button onClick={handleExport}
            className="w-full text-left px-3 py-2 text-sm text-ops-subtext rounded-lg hover:bg-ops-surface0 hover:text-ops-text transition-colors">
            📥 导出聊天记录 (Markdown)
          </button>
          <button onClick={handleClearHistory}
            className="w-full text-left px-3 py-2 text-sm text-ops-alert rounded-lg hover:bg-ops-alert/10 transition-colors">
            🗑️ 清空聊天记录
          </button>
        </div>
        <button onClick={closeModal} className="w-full mt-3 text-xs text-ops-overlay hover:text-ops-subtext text-center py-1">
          关闭
        </button>
      </div>
    </div>
  )
}
