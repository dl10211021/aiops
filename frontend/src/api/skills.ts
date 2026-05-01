import type { SkillInfo, SkillValidationResult } from '@/types'
import { request } from './http'

export async function getSkillRegistry() {
  return request<{ registry: SkillInfo[] }>('/skills/registry')
}

export async function getSkillDetail(skillId: string) {
  return request<{ instructions: string; source_path: string }>(
    `/skills/registry/${skillId}`
  )
}

export async function scanSkills() {
  return request('/skills/scan', { method: 'POST' })
}

export async function migrateSkill(sourcePath: string, targetDirName: string) {
  return request('/skills/migrate', {
    method: 'POST',
    body: JSON.stringify({ source_path: sourcePath, target_dir_name: targetDirName }),
  })
}

export async function createSkill(params: {
  skill_id: string; description: string; instructions: string;
  script_name?: string; script_content?: string; overwrite_existing?: boolean;
}) {
  return request('/skills/create', { method: 'POST', body: JSON.stringify(params) })
}

export async function validateSkill(params: {
  skill_id: string; file_name?: string; content: string;
}) {
  return request<SkillValidationResult>('/skills/validate', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}
