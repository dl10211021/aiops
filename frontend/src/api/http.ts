import type { ApiResponse } from '@/types'

const BASE = '/api/v1'

export function apiUrl(path: string): string {
  return `${BASE}${path}`
}

type ApiErrorCategory = 'credential' | 'connection' | 'internal' | string

type ApiErrorInfo = {
  message: string
  code?: string
  category?: ApiErrorCategory
  status?: number
  raw?: unknown
}

export class OpsApiError extends Error {
  code?: string
  category?: ApiErrorCategory
  status?: number
  raw?: unknown

  constructor(info: ApiErrorInfo) {
    super(info.message)
    this.name = 'OpsApiError'
    this.code = info.code
    this.category = info.category
    this.status = info.status
    this.raw = info.raw
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function stringifyDetail(value: unknown): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (!isRecord(item)) return String(item)
        const loc = Array.isArray(item.loc) ? item.loc.join('.') : ''
        const msg = typeof item.msg === 'string' ? item.msg : ''
        return [loc, msg].filter(Boolean).join(': ')
      })
      .filter(Boolean)
      .join('；')
  }
  if (isRecord(value)) {
    const nested = value.detail || value.message || value.error
    if (nested && nested !== value) return stringifyDetail(nested)
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

export function responseErrorMessage(payload: unknown, fallback: string) {
  if (!isRecord(payload)) return fallback || '请求处理失败'
  return (
    stringifyDetail(payload.detail)
    || stringifyDetail(payload.message)
    || stringifyDetail(payload.error)
    || fallback
    || '请求处理失败'
  )
}

export function isAbortError(error: unknown) {
  return (
    error instanceof DOMException && error.name === 'AbortError'
  ) || (
    isRecord(error) && error.name === 'AbortError'
  )
}

function classifyErrorMessage(message: string): Pick<ApiErrorInfo, 'code' | 'category'> {
  const text = message.toLowerCase()
  if (
    message.includes('密码错误') ||
    message.includes('认证失败') ||
    text.includes('authentication failed') ||
    text.includes('access denied') ||
    text.includes('ora-01017') ||
    text.includes('invalid username/password')
  ) {
    return { code: 'credential_invalid', category: 'credential' }
  }
  if (
    message.includes('连接失败') ||
    message.includes('无法连接') ||
    text.includes('failed to fetch') ||
    text.includes('connection refused') ||
    text.includes('timed out') ||
    text.includes('timeout')
  ) {
    return { code: 'connection_failed', category: 'connection' }
  }
  if (message.includes('内部错误')) {
    return { code: 'internal_error', category: 'internal' }
  }
  return {}
}

function errorInfoFromObject(value: unknown, status?: number): ApiErrorInfo | null {
  if (!isRecord(value)) return null
  const message = stringifyDetail(value.message)
  if (!message) return null
  const code = typeof value.code === 'string' ? value.code : undefined
  const category = typeof value.category === 'string' ? value.category : undefined
  return {
    message,
    code,
    category,
    status,
    raw: value.raw_error || value.raw || value,
  }
}

function responseErrorInfo(payload: unknown, fallback: string, status?: number): ApiErrorInfo {
  if (isRecord(payload)) {
    const dataError = isRecord(payload.data) && isRecord(payload.data.error) ? payload.data.error : null
    const candidates = [payload.detail, dataError, payload.error, payload.message]
    for (const candidate of candidates) {
      const info = errorInfoFromObject(candidate, status)
      if (info) return info
    }
  }
  const message = responseErrorMessage(payload, fallback)
  return { message, status, raw: payload, ...classifyErrorMessage(message) }
}

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('OPSCORE_API_TOKEN')
  return token ? { 'X-API-Key': token } : {}
}

export async function request<T = Record<string, unknown>>(
  path: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  let res: Response
  try {
    res = await fetch(apiUrl(path), {
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...options?.headers },
      ...options,
    })
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new OpsApiError({
      message: '连接失败：无法连接 OpsCore 后端服务，请确认服务已启动或网络正常。',
      code: 'backend_unreachable',
      category: 'connection',
      raw: error,
    })
  }
  const payload = await res.json().catch(() => null)
  if (!res.ok) {
    throw new OpsApiError(responseErrorInfo(payload, res.statusText, res.status))
  }
  if (isRecord(payload) && payload.status === 'error') {
    throw new OpsApiError(responseErrorInfo(payload, '请求处理失败', res.status))
  }
  return payload as ApiResponse<T>
}
