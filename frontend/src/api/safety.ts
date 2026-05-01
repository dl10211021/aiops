import type { SafetyPolicy, SafetyPolicyTestInput, SafetyPolicyTestResult } from '@/types'
import { request } from './http'

export async function getSafetyPolicy() {
  return request<{ policy: SafetyPolicy }>('/config/safety-policy')
}

export async function updateSafetyPolicy(policy: SafetyPolicy) {
  return request<{ policy: SafetyPolicy }>('/config/safety-policy', {
    method: 'POST',
    body: JSON.stringify({ policy }),
  })
}

export async function testSafetyPolicy(input: SafetyPolicyTestInput) {
  return request<{ result: SafetyPolicyTestResult }>('/config/safety-policy/test', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
