import { request } from './http'
import type { RealtimeCanvasItem } from '@/types'

export interface RealtimeCanvasOptions {
  metrics: Array<{ id: string; label: string }>
  kinds: Array<{ id: string; label: string }>
  modes: Array<{ id: string; label: string }>
  intervals: number[]
  durations: number[]
  default_ai_prompt?: string
  default_python_collector?: string
}

export interface RealtimeCanvasStartPayload {
  session_id: string
  kind?: string
  mode?: string
  metrics: string[]
  interval_seconds: number
  duration_seconds: number
  title?: string
  stop_existing?: boolean
  scripts?: Record<string, string>
  collector_code?: string
  canvas_spec?: Record<string, unknown>
  data_schema?: Record<string, unknown>
  html?: string
  ai_prompt_template?: string
}

export async function getRealtimeCanvasOptions() {
  return request<RealtimeCanvasOptions>('/realtime-canvas/options')
}

export async function listRealtimeCanvases() {
  return request<{ items: RealtimeCanvasItem[] }>('/realtime-canvas')
}

export async function getRealtimeCanvas(id: string) {
  return request<{ item: RealtimeCanvasItem }>(`/realtime-canvas/${id}`)
}

export async function startRealtimeCanvas(payload: RealtimeCanvasStartPayload) {
  return request<{ item: RealtimeCanvasItem }>('/realtime-canvas/start', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function stopRealtimeCanvas(id: string) {
  return request<{ item: RealtimeCanvasItem }>(`/realtime-canvas/${id}/stop`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function updateRealtimeCanvas(id: string, payload: Partial<RealtimeCanvasStartPayload> & { scripts?: Record<string, string> }) {
  return request<{ item: RealtimeCanvasItem }>(`/realtime-canvas/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function deleteRealtimeCanvas(id: string) {
  return request<Record<string, never>>(`/realtime-canvas/${id}`, {
    method: 'DELETE',
  })
}

export async function extendRealtimeCanvas(id: string, durationSeconds = 10 * 60) {
  return request<{ item: RealtimeCanvasItem }>(`/realtime-canvas/${id}/extend`, {
    method: 'POST',
    body: JSON.stringify({ duration_seconds: durationSeconds }),
  })
}
