import type {
  ObservabilityOverview,
  ObservabilityDiscoveryCandidate,
  ObservabilityEvidence,
  ObservabilityInvestigation,
  ObservabilityComponent,
  ObservabilityProfile,
  ObservabilityProfilePack,
  ObservabilitySource,
  ObservabilitySystemSummary,
} from '@/types'
import { request } from './http'

export async function getObservabilityOverview() {
  return request<{ overview: ObservabilityOverview }>('/observability/overview')
}

export async function getObservabilitySystems() {
  return request<{ systems: ObservabilitySystemSummary[] }>('/observability/systems')
}

export async function getObservabilityProfile(systemId: string) {
  return request<{ profile: ObservabilityProfile }>(`/observability/systems/${encodeURIComponent(systemId)}`)
}

export async function bindObservabilityAsset(systemId: string, asset: Record<string, unknown>) {
  return request<{ profile: ObservabilityProfile; summary: ObservabilitySystemSummary }>(
    `/observability/systems/${encodeURIComponent(systemId)}/assets`,
    {
      method: 'POST',
      body: JSON.stringify({ asset }),
    },
  )
}

export async function bindObservabilitySession(systemId: string, session: Record<string, unknown>, role = 'investigation_channel') {
  return request<{ profile: ObservabilityProfile; summary: ObservabilitySystemSummary }>(
    `/observability/systems/${encodeURIComponent(systemId)}/sessions`,
    {
      method: 'POST',
      body: JSON.stringify({ session, role }),
    },
  )
}

export async function unbindObservabilityComponent(systemId: string, componentId: string) {
  return request<{ profile: ObservabilityProfile; summary: ObservabilitySystemSummary }>(
    `/observability/systems/${encodeURIComponent(systemId)}/components/${encodeURIComponent(componentId)}`,
    { method: 'DELETE' },
  )
}

export async function updateObservabilityComponent(systemId: string, componentId: string, payload: Partial<ObservabilityComponent>) {
  return request<{ profile: ObservabilityProfile; summary: ObservabilitySystemSummary }>(
    `/observability/systems/${encodeURIComponent(systemId)}/components/${encodeURIComponent(componentId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  )
}

export async function getObservableSources() {
  return request<{ sources: ObservabilitySource[] }>('/observability/sources')
}

export async function getObservabilityDiscoveryCandidates(systemId?: string) {
  const query = systemId ? `?system_id=${encodeURIComponent(systemId)}` : ''
  return request<{ candidates: ObservabilityDiscoveryCandidate[] }>(`/observability/discovery-candidates${query}`)
}

export async function getObservabilityInvestigations(systemId?: string) {
  const query = systemId ? `?system_id=${encodeURIComponent(systemId)}` : ''
  return request<{ investigations: ObservabilityInvestigation[] }>(`/observability/investigations${query}`)
}

export async function createObservabilityInvestigation(payload: {
  system_id: string
  title: string
  symptom: string
  time_window?: string
  severity?: 'unknown' | 'info' | 'warning' | 'critical' | string
}) {
  return request<{ investigation: ObservabilityInvestigation }>('/observability/investigations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function appendObservabilityEvidence(investigationId: string, payload: {
  title: string
  summary?: string
  evidence_type?: string
  task_id?: string
  component_id?: string
  source_id?: string
  raw_ref?: string
  raw_excerpt?: string
  tool_evidence?: Record<string, unknown>
  confidence?: string
}) {
  return request<{ evidence: ObservabilityEvidence; investigation: ObservabilityInvestigation }>(
    `/observability/investigations/${encodeURIComponent(investigationId)}/evidence`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export async function appendObservabilityRunTraceEvidence(investigationId: string, payload: {
  session_id: string
  evidence_id?: string
  tool_call_id?: string
  tool?: string
  title?: string
  summary?: string
  confidence?: string
}) {
  return request<{ evidence: ObservabilityEvidence; investigation: ObservabilityInvestigation }>(
    `/observability/investigations/${encodeURIComponent(investigationId)}/run-trace-evidence`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export async function appendObservabilityRootCause(investigationId: string, payload: {
  title: string
  description?: string
  likelihood?: string
  impact?: string
  confidence?: string
  supporting_evidence_ids?: string[]
  recommended_next_steps?: string[]
}) {
  return request<{ investigation: ObservabilityInvestigation }>(
    `/observability/investigations/${encodeURIComponent(investigationId)}/root-causes`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export async function getObservabilityProfilePacks() {
  return request<{ profile_packs: ObservabilityProfilePack[] }>('/observability/profile-packs')
}
