import { request } from './http'

export async function getHydrateStatus() {
  return request<{ total: number; done: number; success: number; running: boolean }>(
    '/hydrate/status'
  )
}
