import { OpsApiError } from '@/api/client'
import type { ConnectionFeedback } from './connectionModalTypes'

export function connectionFeedbackFromError(error: unknown, fallback = '连接失败'): ConnectionFeedback {
  const message = error instanceof Error ? error.message : fallback
  const category = error instanceof OpsApiError ? error.category : undefined
  const code = error instanceof OpsApiError ? error.code : undefined
  if (category === 'credential' || code === 'credential_invalid') {
    return { ok: false, title: '密码错误', msg: message, category: 'credential' }
  }
  if (category === 'connection' || code === 'connection_failed' || code === 'backend_unreachable') {
    return { ok: false, title: '连接失败', msg: message, category: 'connection' }
  }
  if (category === 'internal' || code === 'internal_error') {
    return { ok: false, title: '内部错误', msg: message, category: 'internal' }
  }
  return { ok: false, title: '连接失败', msg: message || fallback, category }
}
