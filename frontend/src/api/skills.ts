import type { ApiResponse, SkillInfo, SkillValidationResult } from '@/types'
import { request } from './http'

type SkillCacheOptions = {
  forceRefresh?: boolean
}

type CachedSkillRegistryRequest = {
  expiresAt: number
  request: Promise<ApiResponse<{ registry: SkillInfo[] }>>
}

const SKILL_REGISTRY_CACHE_TTL_MS = 60_000

let skillRegistryRequest: CachedSkillRegistryRequest | null = null

export function clearSkillRegistryCache() {
  skillRegistryRequest = null
}

export async function getSkillRegistry(options?: SkillCacheOptions) {
  if (
    !options?.forceRefresh
    && skillRegistryRequest
    && skillRegistryRequest.expiresAt > Date.now()
  ) {
    return skillRegistryRequest.request
  }
  skillRegistryRequest = {
    expiresAt: Date.now() + SKILL_REGISTRY_CACHE_TTL_MS,
    request: request<{ registry: SkillInfo[] }>('/skills/registry').catch((error) => {
      skillRegistryRequest = null
      throw error
    }),
  }
  return skillRegistryRequest.request
}

export async function getSkillDetail(skillId: string) {
  return request<{ instructions: string; source_path: string }>(
    `/skills/registry/${skillId}`
  )
}

export async function scanSkills() {
  const response = await request('/skills/scan', { method: 'POST' })
  clearSkillRegistryCache()
  return response
}

export async function migrateSkill(sourcePath: string, targetDirName: string) {
  const response = await request('/skills/migrate', {
    method: 'POST',
    body: JSON.stringify({ source_path: sourcePath, target_dir_name: targetDirName }),
  })
  clearSkillRegistryCache()
  return response
}

export async function createSkill(params: {
  skill_id: string; description: string; instructions: string;
  script_name?: string; script_content?: string; overwrite_existing?: boolean;
}) {
  const response = await request('/skills/create', { method: 'POST', body: JSON.stringify(params) })
  clearSkillRegistryCache()
  return response
}

export async function validateSkill(params: {
  skill_id: string; file_name?: string; content: string;
}) {
  return request<SkillValidationResult>('/skills/validate', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}
